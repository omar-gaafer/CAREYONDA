import { describe, expect, it } from "vitest";
import data from "../infrastructure/fixtures/investigations.json";
import { parseInvestigationCases } from "./investigation";
const copy = () => structuredClone(data);
describe("M2 investigation boundary", () => {
  it("round trips genuine precomputed engine results with all abstention modes", () => {
    const rows = parseInvestigationCases(data);
    expect(parseInvestigationCases(JSON.parse(JSON.stringify(rows)))).toEqual(
      rows,
    );
    expect(rows.map((c) => c.result.status)).toEqual([
      "ranked",
      "insufficient_evidence",
      "ambiguous",
      "conflicting_evidence",
    ]);
    expect(rows.every((c) => c.result.safety_status === "not_evaluated")).toBe(
      true,
    );
    expect(
      rows[1].result.hypotheses.some((h) => h.missing_evidence.length > 0),
    ).toBe(true);
    expect(rows[2].result.hypotheses.filter((h) => h.rank === 1)).toHaveLength(
      2,
    );
  });
  it.each([
    "schema",
    "engine",
    "fixture",
    "safety",
    "rank",
    "finite",
    "selection",
    "unresolved",
    "time",
    "scope",
    "unknown",
    "provenance",
    "duplicate",
  ])("rejects malformed %s", (kind) => {
    const rows = copy();
    const r = rows[0].result;
    // Treat untrusted JSON as a mutable payload for negative boundary checks.
    const payload: Record<string, unknown> = r;
    if (kind === "schema") payload.schema_version = "9.0.0";
    if (kind === "engine") payload.engine_version = "unknown";
    if (kind === "fixture") Object.assign(rows[0], { fixture_version: "2" });
    if (kind === "safety") payload.safety_status = "safe";
    if (kind === "rank") r.hypotheses[0].rank = 0;
    if (kind === "finite")
      r.hypotheses[0].supporting_evidence[0].observed_value = Infinity;
    if (kind === "selection") r.selected_hypothesis = null;
    if (kind === "unresolved") r.observation_ids.push("unknown-id");
    if (kind === "time") {
      r.reference_timestamp = r.timestamp;
      rows[0].reference_context.timestamp = r.timestamp;
    }
    if (kind === "scope")
      Object.assign(rows[0].observations[0].scope, { mission_id: "OTHER" });
    if (kind === "unknown") payload.probability = 0.99;
    if (kind === "provenance")
      rows[0].observations[0].provenance.origin = "measured";
    if (kind === "duplicate") rows.push(rows[0]);
    expect(() => parseInvestigationCases(rows)).toThrow();
  });
  it("accepts an empty source without inventing results", () =>
    expect(parseInvestigationCases([])).toEqual([]));
  it("preserves null selection and missing-reference metadata", () => {
    const item = parseInvestigationCases(data)[1];
    expect(item.result.selected_hypothesis).toBeNull();
    expect(item.result.quality_issues).toHaveLength(3);
    expect(
      item.observations.filter((o) => o.measurement.kind === "unavailable"),
    ).toHaveLength(3);
  });
});
