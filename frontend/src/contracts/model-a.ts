import { z } from "zod";
import { observationSchema } from "./observation";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const time = z.iso.datetime({ offset: true });
const hash = z.string().regex(/^[0-9a-f]{64}$/);
const finite = z.number().finite();
const mode = z.enum(["live", "historical_replay"]);
const availability = z.enum(["available", "unavailable", "incompatible"]);
const scope = z.strictObject({
  mission_id: z.literal("NASA-RR1"),
  spacecraft_id: z.literal("ISS"),
  data_origin: z.enum(["real", "synthetic"]),
  dataset_id: id,
  run_id: id,
});
export const referenceSchema = z.strictObject({
  sample_id: id,
  assessment_mode: mode,
});
export type ModelAReference = z.infer<typeof referenceSchema>;
export const authorizedSchema = z.strictObject({
  api_version: z.literal("1.0.0"),
  correlation_id: id,
  model_availability: availability,
  samples: z
    .array(
      referenceSchema.extend({
        source_event_time: time,
        scope,
        receipt_id: id.nullable(),
      }),
    )
    .max(128),
});
const receipt = z.strictObject({
  record_id: id,
  dataset_id: id,
  dataset_manifest_sha256: hash,
  acquired_at: time,
  source_reference: z.string().min(1),
});
const feature = z.strictObject({
  name: id,
  unit: z.string(),
  value: finite.nullable(),
  observation_ids: z.array(id),
});
const sample = z.strictObject({
  sample_id: id,
  scope,
  event_time_utc: time,
  available_at: time.nullable(),
  assessment_mode: mode,
  historical_source_availability: z.enum(["known", "unknown"]),
  replay_acquired_at: time.nullable(),
  replay_acquisition: receipt.nullable(),
  transformation_version: z.literal("environmental-1.0.0"),
  features: z.array(feature).length(16),
  observations: z.array(observationSchema).min(1),
});
export const contextSchema = z
  .strictObject({
    schema_version: z.literal("1.1.0"),
    interpretation: z.literal("research_only"),
    assessment_mode: mode,
    historical_source_availability: z.enum(["known", "unknown"]),
    replay_acquired_at: time.nullable(),
    source_event_time: time,
    evidence_availability_scope: z.enum(["source_stream", "careyonda_replay"]),
    sample,
    assessed_at: time,
    model: z
      .strictObject({
        model_id: z.literal("careyonda-model-a-nasa-rr1-environment-iforest"),
        model_version: z.literal("1.1.0"),
        feature_schema_version: z.literal("1.0.0"),
        artifact_sha256: hash,
        dataset_manifest_sha256: hash,
      })
      .nullable(),
    availability: z.enum(["available", "unavailable"]),
    compatibility: z.enum(["compatible", "incompatible", "unknown"]),
    status: z.enum(["flagged", "not_flagged", "unassessed", "abstained"]),
    anomaly_score: finite.nullable(),
    threshold: finite.nullable(),
    threshold_method: z.literal("training_score_quantile").nullable(),
    imputed_features: z.array(id),
    abstention_reasons: z.array(z.string().min(1)),
    limitations: z.array(z.string().min(1)).min(1),
  })
  .superRefine((c, ctx) => {
    const fail = (message: string) => ctx.addIssue({ code: "custom", message });
    if (
      c.assessment_mode !== c.sample.assessment_mode ||
      c.source_event_time !== c.sample.event_time_utc ||
      c.replay_acquired_at !== c.sample.replay_acquired_at ||
      c.historical_source_availability !==
        c.sample.historical_source_availability
    )
      fail("Inconsistent context provenance");
    if (c.sample.scope.data_origin !== "real")
      fail("Unsupported model source origin");
    const expected = [
      ["cabin_co2_concentration", "ppm"],
      ["environment_temperature", "degC"],
      ["relative_humidity", "%"],
    ].flatMap(([m, u]) =>
      ["value", "mean_30m", "delta", "count_30m", "missing"].map((s) => [
        `${m}_${s}`,
        ["count_30m", "missing"].includes(s) ? "1" : u,
      ]),
    );
    expected.push(["gap_seconds", "s"]);
    if (
      c.sample.features.some(
        (f, i) => f.name !== expected[i][0] || f.unit !== expected[i][1],
      )
    )
      fail("Invalid feature schema/units");
    const ids = new Set(c.sample.observations.map((o) => o.observation_id));
    if (
      ids.size !== c.sample.observations.length ||
      c.sample.features.some((f) => f.observation_ids.some((i) => !ids.has(i)))
    )
      fail("Unresolved evidence lineage");
    if (
      c.sample.observations.some(
        (o) =>
          o.scope.kind !== "spacecraft" ||
          o.scope.spacecraft_id !== "ISS" ||
          o.scope.mission_id !== "NASA-RR1" ||
          o.provenance.origin !== "measured" ||
          Date.parse(o.timestamp) > Date.parse(c.source_event_time),
      )
    )
      fail("Unsupported environmental evidence scope/origin");
    if (
      new Set(c.imputed_features).size !== c.imputed_features.length ||
      c.imputed_features.some(
        (name) =>
          !c.sample.features.some((f) => f.name === name && f.value === null),
      )
    )
      fail("Invalid imputation lineage");
    const replay = c.assessment_mode === "historical_replay";
    const effective = replay ? c.replay_acquired_at : c.sample.available_at;
    if (
      !effective ||
      Date.parse(effective) > Date.parse(c.assessed_at) ||
      Date.parse(c.source_event_time) > Date.parse(c.assessed_at)
    )
      fail("Evidence unavailable at assessment");
    if (replay) {
      if (
        c.historical_source_availability !== "unknown" ||
        c.evidence_availability_scope !== "careyonda_replay" ||
        c.sample.available_at !== null ||
        !c.sample.replay_acquisition ||
        c.sample.replay_acquisition.acquired_at !== c.replay_acquired_at ||
        c.sample.replay_acquisition.dataset_id !== c.sample.scope.dataset_id ||
        c.sample.observations.some((o) => o.ingested_at != null)
      )
        fail("Invalid replay availability");
    } else if (
      c.historical_source_availability !== "known" ||
      c.evidence_availability_scope !== "source_stream" ||
      c.replay_acquired_at !== null ||
      c.sample.replay_acquisition !== null ||
      c.sample.observations.some(
        (o) =>
          !o.ingested_at || Date.parse(o.ingested_at) > Date.parse(effective!),
      )
    )
      fail("Invalid live availability");
    if ((c.threshold === null) !== (c.threshold_method === null))
      fail("Invalid threshold provenance");
    if (c.status === "abstained") {
      if (c.anomaly_score !== null || !c.abstention_reasons.length)
        fail("Invalid abstention");
    } else {
      if (
        !c.model ||
        c.anomaly_score === null ||
        c.availability !== "available" ||
        c.compatibility !== "compatible" ||
        c.abstention_reasons.length
      )
        fail("Invalid scored state");
      const status =
        c.threshold === null
          ? "unassessed"
          : c.anomaly_score! >= c.threshold
            ? "flagged"
            : "not_flagged";
      if (c.status !== status)
        fail("Flag contradicts inclusive threshold rule");
    }
  });
export const modelAResponseSchema = z
  .strictObject({
    api_version: z.literal("1.0.0"),
    correlation_id: id,
    model_availability: availability,
    contexts: z.array(contextSchema).max(2),
    limitations: z.array(z.string()).min(1),
  })
  .superRefine((r, c) => {
    if (r.model_availability !== "available" && r.contexts.length)
      c.addIssue({
        code: "custom",
        message: "Unavailable model returned contexts",
      });
  });
export type ModelAResponse = z.infer<typeof modelAResponseSchema>;
