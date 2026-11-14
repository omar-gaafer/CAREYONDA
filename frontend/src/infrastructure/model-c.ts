import {
  localSubmissionSchema,
  modelCResponseSchema,
  type LocalSubmission,
  type ModelCResponse,
} from "../contracts/model-c";
import type { Fetcher } from "./http";

export class ModelCError extends Error {
  constructor(
    public kind: "invalid" | "backend" | "contract",
    public code?: string,
    public correlation?: string,
  ) {
    super(kind);
  }
}

/** Single local request; no cookies, cache, storage, retries or third parties. */
export function createModelCClient(
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
  return {
    async assess(submission: LocalSubmission): Promise<ModelCResponse> {
      const body = localSubmissionSchema.parse(submission);
      let response: Response;
      try {
        response = await fetcher(
          url.origin + "/api/v1/model-c/local-assessments",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            credentials: "omit",
            cache: "no-store",
            redirect: "error",
            signal: AbortSignal.timeout(10000),
          },
        );
      } catch {
        throw new ModelCError("backend");
      }
      const correlation = response.headers.get("X-Correlation-ID") ?? undefined;
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        throw new ModelCError(response.ok ? "contract" : "backend");
      }
      if (!response.ok) {
        const code =
          typeof data === "object" &&
          data !== null &&
          "error" in data &&
          typeof (data as { error: { code?: unknown } }).error?.code ===
            "string"
            ? (data as { error: { code: string } }).error.code
            : undefined;
        throw new ModelCError(
          response.status === 422 ? "invalid" : "backend",
          code,
          correlation,
        );
      }
      const parsed = modelCResponseSchema.safeParse(data);
      if (
        !parsed.success ||
        (correlation && parsed.data.correlation_id !== correlation) ||
        parsed.data.result.subject_id !== body.participant_id
      )
        throw new ModelCError("contract", undefined, correlation);
      return parsed.data;
    },
  };
}
export type ModelCClient = ReturnType<typeof createModelCClient>;
