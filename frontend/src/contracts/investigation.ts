import { z } from "zod";
import { observationSchema } from "./observation";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const time = z.iso.datetime({ offset: true });
const relation = z.enum([
  "above_reference",
  "below_reference",
  "within_reference",
  "active",
  "inactive",
  "fatigue_reported",
  "rested_reported",
  "missing",
  "conflicting",
]);
const hypothesisId = z.enum([
  "baseline",
  "elevated_co2",
  "sleep_deprivation",
  "recent_exercise",
]);
export const evidenceFindingSchema = z.strictObject({
  metric: id,
  relation,
  observation_ids: z.array(id),
  reference_observation_ids: z.array(id).default([]),
  observed_value: z.number().finite().nullable().default(null),
  unit: z.string(),
  reference_minimum: z.number().finite().nullable().default(null),
  reference_maximum: z.number().finite().nullable().default(null),
  explanation: z.string(),
});
export const evidenceQualityIssueSchema = z.strictObject({
  window: z.enum(["current", "reference"]),
  observation_id: id,
  metric: id,
  status: z.enum(["valid", "suspect", "invalid", "missing", "unavailable"]),
  reason_codes: z.array(id),
});
export const hypothesisSchema = z.strictObject({
  hypothesis_id: hypothesisId,
  rank: z.number().int().min(1),
  compatibility: z.enum([
    "supported",
    "partial",
    "mixed",
    "contradicted",
    "insufficient",
  ]),
  expected_relations: z.record(id, relation),
  supporting_evidence: z.array(evidenceFindingSchema),
  contradictory_evidence: z.array(evidenceFindingSchema),
  missing_evidence: z.array(evidenceFindingSchema),
  explanation: z.string(),
  uncertainty: z.array(z.string()),
});
export const investigationSchema = z.strictObject({
  schema_version: z.literal("1.0.0").default("1.0.0"),
  engine_version: z
    .literal("reference-rules-1.0.0")
    .default("reference-rules-1.0.0"),
  investigation_id: id,
  sample_id: id,
  timestamp: time,
  reference_sample_id: id,
  reference_timestamp: time,
  window_seconds: z.number().int().positive(),
  status: z.enum([
    "ranked",
    "ambiguous",
    "insufficient_evidence",
    "conflicting_evidence",
  ]),
  selected_hypothesis: hypothesisId.nullable(),
  hypotheses: z.array(hypothesisSchema),
  observation_ids: z.array(id),
  reference_observation_ids: z.array(id),
  uncertainty: z.array(z.string()),
  quality_issues: z.array(evidenceQualityIssueSchema),
  safety_status: z.literal("not_evaluated").default("not_evaluated"),
});
const anchorSchema = z.strictObject({
  sample_id: id,
  episode_id: id,
  mission_id: id,
  astronaut_id: id,
  spacecraft_id: id,
  compartment_id: id,
  timestamp: time,
});
export const investigationCaseSchema = z
  .strictObject({
    fixture_version: z.literal("1.0.0"),
    origin: z.enum(["synthetic_precomputed", "synthetic_api"]),
    title: z.string(),
    context: anchorSchema,
    reference_context: anchorSchema,
    result: investigationSchema,
    observations: z.array(observationSchema),
  })
  .superRefine((item, ctx) => {
    const fail = (message: string) => ctx.addIssue({ code: "custom", message });
    const r = item.result,
      lookup = new Map(item.observations.map((o) => [o.observation_id, o]));
    if (lookup.size !== item.observations.length) fail("Duplicate evidence ID");
    if (
      r.timestamp !== item.context.timestamp ||
      r.reference_timestamp !== item.reference_context.timestamp ||
      r.sample_id !== item.context.sample_id ||
      r.reference_sample_id !== item.reference_context.sample_id
    )
      fail("Result and anchor context disagree");
    if (
      Date.parse(r.reference_timestamp) >
      Date.parse(r.timestamp) - r.window_seconds * 1000
    )
      fail("Overlapping reference window");
    if (item.observations.some((o) => o.provenance.origin !== "simulated"))
      fail("Demo evidence must be simulated");
    const supported = r.hypotheses.filter(
      (h) => h.compatibility === "supported",
    );
    if (
      new Set(r.hypotheses.map((h) => h.hypothesis_id)).size !==
      r.hypotheses.length
    )
      fail("Duplicate hypothesis");
    if (
      r.status === "ranked"
        ? supported.length !== 1 ||
          r.selected_hypothesis !== supported[0]?.hypothesis_id
        : r.selected_hypothesis !== null
    )
      fail("Selection and abstention disagree");
    if (r.status === "ambiguous" && supported.length < 2)
      fail("Ambiguous selection requires competing support");
    if (r.status === "insufficient_evidence" && supported.length !== 0)
      fail("Insufficient status cannot contain a fully supported pattern");
    const current = new Set(r.observation_ids),
      reference = new Set(r.reference_observation_ids);
    for (const [ids, anchor] of [
      [r.observation_ids, item.context],
      [r.reference_observation_ids, item.reference_context],
    ] as const) {
      if (new Set(ids).size !== ids.length) fail("Duplicate lineage ID");
      for (const oid of ids) {
        const o = lookup.get(oid);
        if (!o) {
          fail("Unresolved evidence ID");
          continue;
        }
        const t = Date.parse(o.timestamp),
          end = Date.parse(anchor.timestamp);
        if (
          t <= end - r.window_seconds * 1000 ||
          t > end ||
          o.scope.mission_id !== anchor.mission_id ||
          (o.scope.kind === "astronaut" &&
            o.scope.astronaut_id !== anchor.astronaut_id) ||
          (o.scope.kind === "spacecraft" &&
            o.scope.spacecraft_id !== anchor.spacecraft_id) ||
          (o.scope.kind === "compartment" &&
            (o.scope.spacecraft_id !== anchor.spacecraft_id ||
              o.scope.compartment_id !== anchor.compartment_id))
        )
          fail("Evidence outside window or scope");
      }
    }
    let conflict = false;
    for (const h of r.hypotheses)
      for (const f of [
        ...h.supporting_evidence,
        ...h.contradictory_evidence,
        ...h.missing_evidence,
      ]) {
        if (
          f.observation_ids.some((oid) => !current.has(oid)) ||
          f.reference_observation_ids.some((oid) => !reference.has(oid))
        )
          fail("Finding outside lineage");
        if (f.relation === "conflicting") conflict = true;
      }
    if (conflict !== (r.status === "conflicting_evidence"))
      fail("Conflict status mismatch");
    for (const q of r.quality_issues)
      if (
        !(q.window === "current" ? current : reference).has(q.observation_id) ||
        lookup.get(q.observation_id)?.metric !== q.metric
      )
        fail("Quality issue outside lineage");
  });
export type Investigation = z.infer<typeof investigationSchema>;
export type InvestigationCase = z.infer<typeof investigationCaseSchema>;
export type EvidenceFinding = z.infer<typeof evidenceFindingSchema>;
export function parseInvestigationCases(payload: unknown): InvestigationCase[] {
  const rows = z.array(investigationCaseSchema).parse(payload);
  if (new Set(rows.map((c) => c.result.investigation_id)).size !== rows.length)
    throw new Error("Duplicate investigation");
  return rows;
}
