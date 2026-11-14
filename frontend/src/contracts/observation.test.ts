import { describe, expect, it } from "vitest";
import { createFixtures, filterObservations } from "../testing/observations";
import { parseObservations } from "./observation";
const sample = () => structuredClone(createFixtures()[0]);
describe("versioned observation boundary", () => {
  it("reproduces deterministic synthetic fixtures and round-trips JSON", () => {
    const rows = createFixtures();
    expect(rows).toEqual(createFixtures());
    expect(rows).toHaveLength(480);
    expect(parseObservations(JSON.parse(JSON.stringify(rows)))).toEqual(rows);
    expect(rows.every((o) => o.provenance.origin === "simulated")).toBe(true);
    expect(rows.some((o) => o.quality.status === "missing")).toBe(true);
    expect(rows.some((o) => o.quality.status === "invalid")).toBe(true);
  });
  it.each([
    "unit",
    "timezone",
    "version",
    "unknown",
    "nonfinite",
    "ingestion",
    "quality",
    "domain",
    "scope",
    "confidence",
  ])("rejects invalid %s without substituting values", (kind) => {
    const row = sample();
    const payload = JSON.parse(JSON.stringify(row));
    if (kind === "unit") payload.measurement.unit = "ppm";
    if (kind === "timezone") payload.timestamp = "2026-11-13T12:00:00";
    if (kind === "version") payload.schema_version = "2.0.0";
    if (kind === "unknown") payload.extra = "unexpected";
    if (kind === "nonfinite") payload.measurement.value = Infinity;
    if (kind === "ingestion") payload.ingested_at = "2020-01-01T00:00:00Z";
    if (kind === "quality") payload.quality.status = "missing";
    if (kind === "domain") payload.domain = "radiation";
    if (kind === "scope")
      payload.scope = { kind: "mission", mission_id: "ARES-07" };
    if (kind === "confidence") payload.quality.sensor_confidence = 1.1;
    expect(() => parseObservations([payload])).toThrow();
  });
  it("preserves invalid numeric evidence and missingness", () => {
    const rows = createFixtures();
    const bad = rows.find((o) => o.quality.status === "invalid")!;
    expect(bad.measurement).toEqual({ kind: "numeric", value: 112, unit: "%" });
    expect(
      rows.find((o) => o.quality.status === "missing")!.measurement.kind,
    ).toBe("unavailable");
  });
  it("accepts explicit offsets and rejects unsupported metrics and provenance", () => {
    const row = JSON.parse(JSON.stringify(sample()));
    row.timestamp = "2026-11-13T14:00:00+02:00";
    row.ingested_at = "2026-11-13T12:00:12Z";
    expect(parseObservations([row])[0].timestamp).toBe(row.timestamp);
    row.provenance.origin = "measured";
    expect(() => parseObservations([row])).toThrow();
    row.provenance.source_type = "sensor";
    delete row.provenance.simulation;
    expect(parseObservations([row])[0].provenance.origin).toBe("measured");
    row.metric = "unsupported_metric";
    expect(() => parseObservations([row])).toThrow();
  });
  it("rejects duplicate evidence IDs", () => {
    const row = sample();
    expect(() => parseObservations([row, row])).toThrow("Duplicate");
  });
  it("filters by event-time boundary and isolates crew without removing cabin data", () => {
    const rows = filterObservations(createFixtures(), "crew-02", 6);
    expect(rows).toHaveLength(78);
    expect(
      rows.every(
        (o) =>
          o.scope.kind !== "astronaut" || o.scope.astronaut_id === "crew-02",
      ),
    ).toBe(true);
    expect(rows.some((o) => o.scope.kind === "spacecraft")).toBe(true);
    expect(
      rows.every(
        (o) => Date.parse(o.timestamp) >= Date.parse("2026-11-13T06:00:00Z"),
      ),
    ).toBe(true);
  });
});
