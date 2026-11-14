import {
  parseObservations,
  metrics,
  type Metric,
  type Observation,
} from "../contracts/observation";
export const MISSION_START = "2026-11-01T00:00:00Z";
export const DEMO_NOW = "2026-11-13T12:00:00Z";
export const crew = [
  {
    id: "crew-01",
    name: "Alex Morgan",
    role: "Mission commander",
    initials: "AM",
  },
  {
    id: "crew-02",
    name: "Sam Rivera",
    role: "Flight engineer",
    initials: "SR",
  },
  {
    id: "crew-03",
    name: "Jordan Chen",
    role: "Research specialist",
    initials: "JC",
  },
];
export interface ObservationRepository {
  list(): Promise<unknown>;
}
export function createFixtures(): Observation[] {
  const rows: unknown[] = [];
  const add = (metric: Metric, index: number, person?: string, offset = 0) => {
    const absent = index === 18 && metric === "heart_rate";
    const invalid = index === 30 && metric === "relative_humidity";
    const suspect = index === 35 && metric === "cabin_co2_concentration";
    const values: Partial<Record<Metric, number>> = {
      heart_rate: 72 + offset * 3 + 7 * Math.sin(index / 5),
      sleep_duration: 7.3 + offset / 5,
      cabin_co2_concentration: 730 + 65 * Math.sin(index / 7),
      cabin_co2_partial_pressure: 74 + 6 * Math.sin(index / 7),
      environment_temperature: 22.1 + 0.7 * Math.sin(index / 8),
      relative_humidity: invalid ? 112 : 43 + 4 * Math.sin(index / 6),
    };
    const time = Date.parse(DEMO_NOW) - (47 - index) * 30 * 60_000;
    rows.push({
      schema_version: "1.0.0",
      observation_id: `syn-${person ?? "cabin"}-${metric}-${index}`,
      timestamp: new Date(time).toISOString(),
      ingested_at: new Date(time + 12_000).toISOString(),
      domain: metrics[metric].domain,
      metric,
      scope: person
        ? { kind: "astronaut", astronaut_id: person, mission_id: "ARES-07" }
        : {
            kind: "spacecraft",
            spacecraft_id: "HABITAT-01",
            mission_id: "ARES-07",
          },
      measurement: absent
        ? { kind: "unavailable", reason: "not_received" }
        : {
            kind: "numeric",
            value: Math.round(values[metric]! * 10) / 10,
            unit: metrics[metric].unit,
          },
      quality: {
        status: absent
          ? "missing"
          : invalid
            ? "invalid"
            : suspect
              ? "suspect"
              : "valid",
        reason_codes: absent
          ? ["synthetic_dropout"]
          : invalid
            ? ["physical_domain_violation"]
            : suspect
              ? ["synthetic_sensor_drift"]
              : [],
      },
      provenance: {
        source_type: "simulator",
        source_id: "phase1-fixture",
        method: "deterministic-waveform",
        origin: "simulated",
        parent_observation_ids: [],
        simulation: {
          scenario_id: "frontend-demo",
          run_id: "phase1-v1",
          generator_version: "1.0.0",
          seed: 42,
        },
      },
    });
  };
  for (let i = 0; i < 48; i++) {
    crew.forEach((c, n) => {
      add("heart_rate", i, c.id, n);
      add("sleep_duration", i, c.id, n);
    });
    (
      [
        "cabin_co2_concentration",
        "cabin_co2_partial_pressure",
        "environment_temperature",
        "relative_humidity",
      ] as Metric[]
    ).forEach((m) => add(m, i));
  }
  return parseObservations(rows);
}
export const fixtureRepository: ObservationRepository = {
  async list() {
    return createFixtures();
  },
};
export function filterObservations(
  rows: Observation[],
  crewId: string,
  hours: number,
): Observation[] {
  const cutoff = Date.parse(DEMO_NOW) - hours * 3_600_000;
  return rows.filter(
    (o) =>
      Date.parse(o.timestamp) >= cutoff &&
      Date.parse(o.timestamp) <= Date.parse(DEMO_NOW) &&
      (o.scope.kind !== "astronaut" ||
        crewId === "all" ||
        o.scope.astronaut_id === crewId),
  );
}
