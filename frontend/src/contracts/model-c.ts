import { z } from "zod";

/*
 * Model C local self-report contracts (backend: app/schemas/model_c_local_entry.py
 * and app/schemas/isolation_confinement.py, model 1.1.0). Fields the page renders
 * are validated strictly; deeply nested M4.2 lineage is checked for the parts we
 * display and otherwise passed through unchanged. The server stays authoritative.
 */

export const fatigueCategories = ["rested", "tired", "very_tired"] as const;
export type FatigueCategory = (typeof fatigueCategories)[number];
export const pseudonymPattern = /^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$/;
export const MAX_ENTRIES = 60;
export const MAX_ASSESSMENT_DAYS = 7;

const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const time = z.iso.datetime({ offset: true });
const interval = z.strictObject({ start: time, end: time });
const reasons = z.array(id);
const finite = z.number().refine(Number.isFinite);

export const localEntrySchema = z.strictObject({
  date: z.iso.date(),
  sleep_duration_hours: z.number().min(0).max(24).optional(),
  fatigue: z.enum(fatigueCategories).optional(),
});
export const localSubmissionSchema = z.strictObject({
  schema_version: z.literal("1.0.0"),
  participant_id: z.string().regex(pseudonymPattern),
  assessment_days: z.number().int().min(1).max(MAX_ASSESSMENT_DAYS),
  entries: z.array(localEntrySchema).min(1).max(MAX_ENTRIES),
});
export type LocalSubmission = z.infer<typeof localSubmissionSchema>;

const observationRef = z.looseObject({
  observation_id: id,
  timestamp: time,
  metric: id,
  measurement: z.looseObject({ kind: z.string() }),
  provenance: z.looseObject({
    origin: z.enum(["measured", "self_reported", "derived", "simulated"]),
    source_type: z.string(),
  }),
});
const excluded = z.looseObject({
  evidence: z.looseObject({ observation: observationRef }),
  reason_codes: reasons.min(1),
});
const provenanceNature = z.array(
  z.enum(["direct_measurement", "self_report", "derived", "simulated"]),
);
const instrumentKind = z.enum(["sensor", "self_report_form"]);
const indicatorStatus = z.enum(["assessed", "abstained"]);

const finding = z.looseObject({
  finding_id: id,
  evidence: z.looseObject({
    observation: observationRef,
    sensor_id: id.nullable(),
    sensor_epoch: id.nullable(),
    data_origin: z.enum(["synthetic", "real", "unknown"]),
  }),
  policy: z.looseObject({
    score_definition: z.literal("absolute_deviation_over_raw_mad"),
    threshold_governance: z.enum(["unassessed", "approved_research"]),
  }),
  original_value: finite.nullable(),
  signed_deviation: finite.nullable(),
  raw_mad_score: finite.min(0).nullable(),
  direction: z.enum(["above", "below", "equal", "unassessed"]),
  score_status: z.enum([
    "scored",
    "flat_reference",
    "insufficient_reference",
    "unsupported",
    "invalid_observation",
  ]),
  threshold_status: z.enum(["unassessed", "exceeded", "not_exceeded"]),
  quality_limitations: reasons,
  abstention_reasons: reasons,
  explanation: z.string().min(1),
});
export type ModelCFinding = z.infer<typeof finding>;

const numericIndicator = z.looseObject({
  kind: z.literal("numeric_personal_baseline"),
  indicator: z.literal("sleep_duration"),
  unit: z.literal("h"),
  registry_reporting_mode: z.enum(["unspecified_by_contract", "self_report"]),
  instrument_kind: instrumentKind,
  evidence_provenance: provenanceNature,
  status: indicatorStatus,
  baseline: z.looseObject({
    profile_id: id,
    status: z.enum([
      "ready",
      "unsupported",
      "insufficient_reference",
      "flat_reference",
    ]),
    median_value: finite.nullable(),
    raw_mad: finite.min(0).nullable(),
    method_version: id,
    abstention_reasons: reasons,
    excluded: z.array(excluded),
    summary: z.looseObject({
      total_bins: z.number().int().positive(),
      occupied_bins: z.number().int().min(0),
      sample_count: z.number().int().min(0),
      occupancy_fraction: finite,
      observed_span_seconds: finite,
      maximum_gap_seconds: finite,
    }),
  }),
  findings: z.array(finding),
  summary: z.strictObject({
    findings: z.number().int().min(0),
    scored: z.number().int().min(0),
    above_reference: z.number().int().min(0),
    below_reference: z.number().int().min(0),
    equal_to_reference: z.number().int().min(0),
    abstained: z.number().int().min(0),
    median_raw_mad_score: finite.nullable(),
    maximum_raw_mad_score: finite.nullable(),
    threshold_exceeded: z.number().int().min(0),
  }),
  explanation: z.string().min(1),
  abstention_reasons: reasons,
});
export type NumericIndicator = z.infer<typeof numericIndicator>;

const categoricalIndicator = z.looseObject({
  kind: z.literal("categorical_report_distribution"),
  indicator: z.literal("fatigue_self_report"),
  registry_reporting_mode: z.enum(["unspecified_by_contract", "self_report"]),
  instrument_kind: instrumentKind,
  evidence_provenance: provenanceNature,
  status: indicatorStatus,
  categories: z.array(
    z.strictObject({
      category: z.enum(fatigueCategories),
      reference_count: z.number().int().min(0),
      assessment_count: z.number().int().min(0),
    }),
  ),
  reference_report_ids: reasons,
  assessment_report_ids: reasons,
  excluded: z.array(excluded),
  explanation: z.string().min(1),
  abstention_reasons: reasons,
});
export type CategoricalIndicator = z.infer<typeof categoricalIndicator>;

const result = z.looseObject({
  schema_version: z.literal("1.0.0"),
  interpretation: z.literal("research_only"),
  model_id: z.literal("careyonda-model-c-isolation-confinement"),
  model_version: z.literal("1.1.0"),
  method_version: id,
  assessment_id: id,
  subject_id: id,
  data_origin: z.enum(["synthetic", "real"]),
  assessed_at: time,
  reference_interval: interval,
  assessment_interval: interval,
  parameters: z.looseObject({
    parameter_status: z.enum([
      "unvalidated_research_default",
      "caller_supplied",
    ]),
    bin_duration_seconds: finite,
    minimum_occupied_bins: z.number().int(),
    minimum_reference_reports: z.number().int(),
    maximum_reference_age_seconds: finite,
  }),
  indicators: z
    .array(
      z.discriminatedUnion("kind", [numericIndicator, categoricalIndicator]),
    )
    .min(1),
  status: z.enum(["assessed", "partially_assessed", "abstained"]),
  abstention_reasons: reasons,
  unused_evidence_ids: reasons,
  safety_status: z.literal("not_evaluated"),
  limitations: z.array(z.string().min(1)).min(1),
});

export const modelCResponseSchema = z
  .strictObject({
    api_version: z.literal("1.0.0"),
    correlation_id: z.string().min(1),
    source: z.literal("transient_local_self_report"),
    persistence: z.literal("none"),
    time_convention: z.string().min(1),
    result,
  })
  .superRefine((value, ctx) => {
    for (const item of value.result.indicators) {
      if ((item.status === "assessed") === item.abstention_reasons.length > 0)
        ctx.addIssue({
          code: "custom",
          message: "indicator status contradicts abstention reasons",
        });
      if (item.kind === "numeric_personal_baseline") {
        const scored = item.findings.filter((f) => f.score_status === "scored");
        if (
          scored.length !== item.summary.scored ||
          item.findings.length !== item.summary.findings ||
          scored.some((f) => f.raw_mad_score === null) ||
          item.findings.some(
            (f) => f.score_status !== "scored" && f.raw_mad_score !== null,
          )
        )
          ctx.addIssue({
            code: "custom",
            message: "numeric findings contradict their summary",
          });
      }
    }
  });
export type ModelCResponse = z.infer<typeof modelCResponseSchema>;
