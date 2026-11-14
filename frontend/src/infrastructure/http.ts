import {
  contextsSchema,
  pageSchema,
  investigationResponseSchema,
  type ApiPreset,
} from "../contracts/api";
import { parseObservations } from "../contracts/observation";
import { parseInvestigationCases } from "../contracts/investigation";
import type { ObservationRepository } from "./observations";
import type { InvestigationRepository } from "./investigations";
export type Fetcher = typeof fetch;
export function createHttpRepositories(
  baseUrl: string,
  fetcher: Fetcher = (...args) => fetch(...args),
): {
  observations: ObservationRepository;
  investigations: InvestigationRepository;
} {
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
    throw new Error("API URL must be a credential-free loopback HTTP origin");
  const base = url.origin;
  async function request(path: string, body?: unknown): Promise<unknown> {
    const response = await fetcher(base + "/api/v1" + path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok)
      throw new Error(
        `Local API request failed (${response.status}). No fixture fallback.`,
      );
    return response.json();
  }
  async function listObservations() {
    const rows = [];
    let offset = 0,
      total = 0;
    do {
      const page = pageSchema.parse(
        await request(`/observations?limit=100&offset=${offset}`),
      );
      if (
        page.offset !== offset ||
        page.limit !== 100 ||
        page.items.length !== Math.min(100, page.total - offset) ||
        (offset > 0 && page.total !== total)
      )
        throw new Error("Invalid API pagination");
      total = page.total;
      rows.push(...page.items);
      offset += page.items.length;
      if (!page.items.length && offset < total)
        throw new Error("Incomplete API evidence");
    } while (offset < total);
    const validated = parseObservations(rows);
    if (validated.some((o) => o.provenance.origin !== "simulated"))
      throw new Error(
        "Configured synthetic API returned an unsupported source origin",
      );
    return validated;
  }
  return {
    observations: { list: listObservations },
    investigations: {
      async list() {
        return [];
      },
      async presets() {
        return contextsSchema.parse(await request("/contexts")).presets;
      },
      async submit(preset: ApiPreset) {
        const response = investigationResponseSchema.parse(
          await request("/investigations", {
            schema_version: "1.0.0",
            current: preset.current,
            reference: preset.reference,
            window_seconds: 300,
          }),
        );
        const observations = await listObservations();
        const ids = new Set([
          ...response.result.observation_ids,
          ...response.result.reference_observation_ids,
        ]);
        return parseInvestigationCases([
          {
            fixture_version: "1.0.0",
            origin: "synthetic_api",
            title: preset.title,
            context: preset.current,
            reference_context: preset.reference,
            result: response.result,
            observations: observations.filter((o) => ids.has(o.observation_id)),
          },
        ])[0];
      },
    },
  };
}
