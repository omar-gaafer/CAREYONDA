import {
  authorizedSchema,
  modelAResponseSchema,
  type ModelAReference,
} from "../contracts/model-a";
import type { Fetcher } from "./http";
export class ModelAError extends Error {
  constructor(
    public kind: "unauthorized" | "invalid" | "backend" | "contract",
    public correlation?: string,
  ) {
    super(kind);
  }
}
export function createModelAClient(
  baseUrl: string,
  fetcher: Fetcher = (...args) => fetch(...args),
) {
  const url = new URL(baseUrl);
  if (
    url.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(url.hostname) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("Invalid local API origin");
  async function request(path: string, body?: unknown) {
    let response: Response;
    try {
      response = await fetcher(url.origin + "/api/v1/environmental/" + path, {
        method: body === undefined ? "GET" : "POST",
        headers:
          body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(10000),
      });
    } catch {
      throw new ModelAError("backend");
    }
    if (!response.ok && response.status !== 503)
      throw new ModelAError(
        response.status === 403
          ? "unauthorized"
          : response.status === 422
            ? "invalid"
            : "backend",
        response.headers.get("X-Correlation-ID") ?? undefined,
      );
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new ModelAError("contract");
    }
    return {
      data,
      status: response.status,
      correlation: response.headers.get("X-Correlation-ID"),
    };
  }
  return {
    async list() {
      const { data, correlation } = await request("authorized-samples");
      const result = authorizedSchema.safeParse(data);
      if (
        !result.success ||
        (correlation && result.data.correlation_id !== correlation)
      )
        throw new ModelAError("contract");
      return result.data;
    },
    async assess(reference: ModelAReference, assessedAt: string) {
      const { data, status, correlation } = await request("anomaly-context", {
        schema_version: "1.1.0",
        assessed_at: assessedAt,
        sample_references: [
          {
            sample_id: reference.sample_id,
            assessment_mode: reference.assessment_mode,
          },
        ],
      });
      const result = modelAResponseSchema.safeParse(data);
      if (
        !result.success ||
        (correlation && result.data.correlation_id !== correlation)
      )
        throw new ModelAError("contract");
      if (
        status === 503
          ? result.data.model_availability === "available"
          : result.data.model_availability !== "available" ||
            result.data.contexts.length !== 1
      )
        throw new ModelAError("contract");
      if (
        result.data.contexts.some(
          (c) =>
            c.sample.sample_id !== reference.sample_id ||
            c.assessment_mode !== reference.assessment_mode ||
            Date.parse(c.assessed_at) !== Date.parse(assessedAt),
        )
      )
        throw new ModelAError("contract");
      return result.data;
    },
  };
}
export type ModelAClient = ReturnType<typeof createModelAClient>;
