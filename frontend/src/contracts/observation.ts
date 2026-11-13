import { z } from "zod";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const timestamp = z.iso.datetime({ offset: true });
const scope = z.discriminatedUnion("kind", [
  z.strictObject({
    kind: z.literal("astronaut"),
    astronaut_id: id,
    mission_id: id,
  }),
  z.strictObject({
    kind: z.literal("spacecraft"),
    spacecraft_id: id,
    mission_id: id,
  }),
  z.strictObject({
    kind: z.literal("compartment"),
    spacecraft_id: id,
    compartment_id: id,
    mission_id: id,
  }),
  z.strictObject({ kind: z.literal("mission"), mission_id: id }),
]);
export const metrics = {
  fatigue_self_report: {
    label: "Fatigue self-report",
    unit: "1",
    domain: "behavioral",
    scopes: ["astronaut"],
  },
  exercise_active: {
    label: "Exercise active",
    unit: "1",
    domain: "mission_context",
    scopes: ["astronaut", "mission"],
  },
  communication_delay: {
    label: "Communication delay",
    unit: "s",
    domain: "mission_context",
    scopes: ["spacecraft", "mission"],
  },
  heart_rate: {
    label: "Heart rate",
    unit: "bpm",
    domain: "physiological",
    scopes: ["astronaut"],
  },
  sleep_duration: {
    label: "Reported sleep",
    unit: "h",
    domain: "behavioral",
    scopes: ["astronaut"],
  },
  cabin_co2_concentration: {
    label: "CO₂ concentration",
    unit: "ppm",
    domain: "environmental",
    scopes: ["spacecraft", "mission"],
  },
  cabin_co2_partial_pressure: {
    label: "CO₂ partial pressure",
    unit: "Pa",
    domain: "environmental",
    scopes: ["spacecraft", "compartment"],
  },
  environment_temperature: {
    label: "Temperature",
    unit: "degC",
    domain: "environmental",
    scopes: ["spacecraft", "mission"],
  },
  relative_humidity: {
    label: "Relative humidity",
    unit: "%",
    domain: "environmental",
    scopes: ["spacecraft", "mission"],
  },
} as const;
export type Metric = keyof typeof metrics;
const metric = z.enum(Object.keys(metrics) as [Metric, ...Metric[]]);
export const observationSchema = z
  .strictObject({
    schema_version: z.literal("1.0.0"),
    observation_id: id,
    timestamp,
    ingested_at: timestamp.nullable().optional(),
    domain: z.enum([
      "physiological",
      "environmental",
      "radiation",
      "behavioral",
      "altered_gravity",
      "mission_context",
    ]),
    metric,
    scope,
    measurement: z.discriminatedUnion("kind", [
      z.strictObject({
        kind: z.literal("numeric"),
        value: z.number().finite(),
        unit: z.string().min(1).max(32),
      }),
      z.strictObject({ kind: z.literal("boolean"), value: z.boolean() }),
      z.strictObject({ kind: z.literal("categorical"), value: id }),
      z.strictObject({
        kind: z.literal("unavailable"),
        reason: z.enum([
          "not_received",
          "not_collected",
          "sensor_offline",
          "rejected",
        ]),
      }),
    ]),
    quality: z.strictObject({
      status: z.enum(["valid", "suspect", "invalid", "missing", "unavailable"]),
      reason_codes: z.array(id).default([]),
      sensor_confidence: z.number().min(0).max(1).nullable().optional(),
    }),
    provenance: z.strictObject({
      source_type: z.enum([
        "sensor",
        "crew_report",
        "computation",
        "simulator",
        "mission_log",
      ]),
      source_id: id,
      method: id,
      origin: z.enum(["measured", "self_reported", "derived", "simulated"]),
      parent_observation_ids: z.array(id).default([]),
      transformation_version: id.nullable().optional(),
      simulation: z
        .strictObject({
          scenario_id: id,
          run_id: id,
          generator_version: id,
          seed: z.number().int().nonnegative(),
        })
        .nullable()
        .optional(),
    }),
  })
  .superRefine((o, ctx) => {
    const fail = (path: string, message: string) =>
      ctx.addIssue({ code: "custom", path: [path], message });
    const definition = metrics[o.metric];
    if (
      o.domain !== definition.domain ||
      !(definition.scopes as readonly string[]).includes(o.scope.kind)
    )
      fail("scope", "Metric domain or scope is incompatible");
    const expectedKind =
      o.metric === "fatigue_self_report"
        ? "categorical"
        : o.metric === "exercise_active"
          ? "boolean"
          : "numeric";
    if (
      o.measurement.kind !== "unavailable" &&
      o.measurement.kind !== expectedKind
    )
      fail("measurement", "Metric measurement kind mismatch");
    if (
      o.metric === "fatigue_self_report" &&
      o.measurement.kind === "categorical" &&
      !["rested", "tired", "very_tired"].includes(o.measurement.value)
    )
      fail("measurement", "Unsupported fatigue state");
    if (
      o.measurement.kind === "numeric" &&
      o.measurement.unit !== definition.unit
    )
      fail("measurement", "Canonical unit required");
    const p = o.provenance;
    const allowed = {
      measured: ["sensor", "mission_log"],
      self_reported: ["crew_report"],
      derived: ["computation"],
      simulated: ["simulator"],
    };
    if (!allowed[p.origin].includes(p.source_type))
      fail("provenance", "Source and origin disagree");
    if ((p.origin === "simulated") !== (p.simulation != null))
      fail("provenance", "Simulation metadata must match origin");
    if (
      p.origin === "derived"
        ? !p.parent_observation_ids.length || !p.transformation_version
        : p.parent_observation_ids.length > 0 ||
          p.transformation_version != null
    )
      fail("provenance", "Derivation metadata must match origin");
    if (
      new Set(p.parent_observation_ids).size !==
        p.parent_observation_ids.length ||
      p.parent_observation_ids.includes(o.observation_id)
    )
      fail("provenance", "Invalid parent identifiers");
    const absent = o.measurement.kind === "unavailable";
    if (absent !== ["missing", "unavailable"].includes(o.quality.status))
      fail("quality", "Absence and quality must agree");
    if (
      o.measurement.kind === "unavailable" &&
      o.quality.status !==
        (o.measurement.reason === "not_received" ? "missing" : "unavailable")
    )
      fail("quality", "Absence reason must match status");
    if (
      (o.quality.status === "valid") !==
      (o.quality.reason_codes.length === 0)
    )
      fail("quality", "Non-valid data requires reason codes");
    if (new Set(o.quality.reason_codes).size !== o.quality.reason_codes.length)
      fail("quality", "Duplicate reason code");
    if (absent && o.quality.sensor_confidence != null)
      fail("quality", "Absent data cannot carry confidence");
    if (o.ingested_at && Date.parse(o.ingested_at) < Date.parse(o.timestamp))
      fail("ingested_at", "Ingestion precedes event");
  });
export type Observation = z.infer<typeof observationSchema>;
// Deliberately supported numeric subset; other backend variants fail explicitly.
export function parseObservations(payload: unknown): Observation[] {
  const data = z.array(observationSchema).parse(payload);
  if (new Set(data.map((o) => o.observation_id)).size !== data.length)
    throw new Error("Duplicate evidence identifiers");
  return data;
}
