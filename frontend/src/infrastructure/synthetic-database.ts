import { z } from "zod";
import { observationSchema } from "../contracts/observation";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/),
  count = z.number().int().nonnegative();
export const catalogSchema = z
  .strictObject({
    api_version: z.literal("1.0.0"),
    source: z.literal("synthetic_database"),
    database_engine: z.literal("Local PostgreSQL"),
    total_seed_rows: count,
    table_counts: z.strictObject({
      missions: count,
      spacecraft: count,
      compartments: count,
      astronaut_profiles: count,
      observations: count,
      numeric_measurements: count,
      boolean_measurements: count,
      categorical_measurements: count,
      unavailable_measurements: count,
      observation_quality_reasons: count,
    }),
    missions: z
      .array(
        z.strictObject({
          mission_id: id,
          spacecraft_ids: z.array(id),
          astronaut_ids: z.array(id),
          source_ids: z.array(id),
          association_basis: z.literal("observation_scope"),
        }),
      )
      .max(2),
  })
  .superRefine((v, ctx) => {
    if (
      Object.values(v.table_counts).reduce((a, b) => a + b, 0) !==
        v.total_seed_rows ||
      new Set(v.missions.map((m) => m.mission_id)).size !== v.missions.length
    )
      ctx.addIssue({ code: "custom", message: "Inconsistent catalog" });
  });
export const pageSchema = z
  .strictObject({
    api_version: z.literal("1.0.0"),
    source: z.literal("synthetic_database"),
    mission_id: id,
    items: z.array(observationSchema).max(100),
    total: count,
    limit: z.number().int().min(1).max(100),
    offset: z.number().int().min(0).max(2000),
    missing: count,
    suspect: count,
  })
  .superRefine((v, ctx) => {
    if (
      new Set(v.items.map((o) => o.observation_id)).size !== v.items.length ||
      v.items.length !== Math.max(0, Math.min(v.limit, v.total - v.offset)) ||
      v.missing + v.suspect > v.total ||
      v.items.some(
        (o, i) =>
          o.scope.mission_id !== v.mission_id ||
          o.provenance.origin !== "simulated" ||
          o.provenance.simulation?.seed !== 42 ||
          (i > 0 &&
            (o.timestamp < v.items[i - 1].timestamp ||
              (o.timestamp === v.items[i - 1].timestamp &&
                o.observation_id < v.items[i - 1].observation_id))),
      )
    )
      ctx.addIssue({
        code: "custom",
        message: "Inconsistent synthetic evidence",
      });
  });
export type SyntheticCatalog = z.infer<typeof catalogSchema>;
export type SyntheticPage = z.infer<typeof pageSchema>;
export function createSyntheticClient(
  baseUrl: string,
  fetcher: typeof fetch = (...args) => fetch(...args),
) {
  const base = new URL(baseUrl);
  if (
    base.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(base.hostname) ||
    base.username ||
    base.password ||
    base.pathname !== "/" ||
    base.search ||
    base.hash
  )
    throw Error("Local API configuration required");
  async function read(path: string, signal: AbortSignal): Promise<unknown> {
    const r = await fetcher(base.origin + "/api/v1/local-synthetic" + path, {
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]),
    });
    if (!r.ok)
      throw Error(
        "Local synthetic database disabled, unavailable or query rejected",
      );
    return r.json();
  }
  return {
    async catalog(signal: AbortSignal) {
      return catalogSchema.parse(await read("/catalog", signal));
    },
    async page(
      mission: string,
      source: string,
      metric: string,
      offset: number,
      signal: AbortSignal,
    ) {
      const q = new URLSearchParams({
        mission_id: mission,
        limit: "100",
        offset: String(offset),
      });
      if (source) q.set("source_id", source);
      if (metric) q.set("metric", metric);
      const p = pageSchema.parse(await read("/observations?" + q, signal));
      if (
        p.mission_id !== mission ||
        p.offset !== offset ||
        p.limit !== 100 ||
        p.items.some(
          (o) =>
            (source && o.provenance.source_id !== source) ||
            (metric && o.metric !== metric),
        )
      )
        throw Error("Query mismatch");
      return p;
    },
  };
}
