import { useEffect, useMemo, useState } from "react";
import {
  createSyntheticClient,
  type SyntheticCatalog,
  type SyntheticPage,
} from "../../infrastructure/synthetic-database";
import {
  Badge,
  PageIntro,
  Panel,
  State,
  Trend,
  ObservationValue,
  utc,
} from "../../shared/ui";
import type { Metric } from "../../contracts/observation";
const numeric = [
  "heart_rate",
  "cabin_co2_partial_pressure",
  "sleep_duration",
  "communication_delay",
] as const;
export function SyntheticDatabase({ apiUrl }: { apiUrl: string }) {
  const [catalog, setCatalog] = useState<SyntheticCatalog | null>(null),
    [page, setPage] = useState<SyntheticPage | null>(null);
  const [mission, setMission] = useState(""),
    [source, setSource] = useState(""),
    [metric, setMetric] = useState("heart_rate"),
    [offset, setOffset] = useState(0),
    [attempt, setAttempt] = useState(0);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const client = useMemo(() => {
    try {
      return createSyntheticClient(apiUrl);
    } catch {
      return null;
    }
  }, [apiUrl]);
  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setCatalog(null);
    setPage(null);
    setError("");
    if (!client) {
      setError("Local API configuration required");
      setLoading(false);
      return;
    }
    client
      .catalog(c.signal)
      .then((v) => {
        if (!c.signal.aborted) {
          setCatalog(v);
          setMission(v.missions[0]?.mission_id ?? "");
          setSource(v.missions[0]?.source_ids[0] ?? "");
          setOffset(0);
        }
      })
      .catch(() => {
        if (!c.signal.aborted) {
          setError(
            "Local synthetic database disabled, unavailable or invalid. No fixture fallback.",
          );
          setLoading(false);
        }
      });
    return () => c.abort();
  }, [client, attempt]);
  useEffect(() => {
    if (!client || !catalog || !mission) return;
    const c = new AbortController();
    setLoading(true);
    setPage(null);
    setError("");
    client
      .page(mission, source, metric, offset, c.signal)
      .then((v) => {
        if (!c.signal.aborted) {
          setPage(v);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!c.signal.aborted) {
          setError(
            "Database query rejected or unavailable. No fixture fallback.",
          );
          setLoading(false);
        }
      });
    return () => c.abort();
  }, [client, catalog, mission, source, metric, offset]);
  const selected = catalog?.missions.find((m) => m.mission_id === mission),
    chartMetric = numeric.includes(metric as (typeof numeric)[number])
      ? (metric as Metric)
      : null;
  return (
    <>
      <PageIntro title="Synthetic Research Dataset">
        <Badge>Local PostgreSQL</Badge>
        <Badge>Not Live Astronaut Telemetry</Badge>
        <p>
          Actual read-only database queries. No AI result or diagnosis is
          inferred.
        </p>
      </PageIntro>
      {error && (
        <State kind="error" retry={() => setAttempt((x) => x + 1)}>
          {error}
        </State>
      )}
      {catalog && (
        <Panel title="Persisted dataset">
          <p>
            {catalog.total_seed_rows.toLocaleString()} database rows ·{" "}
            {catalog.table_counts.observations.toLocaleString()} observations ·{" "}
            {catalog.table_counts.missions} missions ·{" "}
            {catalog.table_counts.spacecraft} spacecraft ·{" "}
            {catalog.table_counts.astronaut_profiles} fictional astronauts
          </p>
          <p>
            Associations are from observation scope, not authenticated
            assignments.
          </p>
          <label>
            Mission
            <select
              aria-label="Synthetic database mission"
              value={mission}
              onChange={(e) => {
                setMission(e.target.value);
                setSource(
                  catalog.missions.find((m) => m.mission_id === e.target.value)
                    ?.source_ids[0] ?? "",
                );
                setOffset(0);
                setPage(null);
              }}
            >
              {catalog.missions.map((m) => (
                <option key={m.mission_id}>{m.mission_id}</option>
              ))}
            </select>
          </label>
          <p>Spacecraft: {selected?.spacecraft_ids.join(", ")}</p>
          <p>
            Fictional astronaut profiles: {selected?.astronaut_ids.join(", ")}
          </p>
          <label>
            Simulator source
            <select
              aria-label="Synthetic database source"
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setOffset(0);
                setPage(null);
              }}
            >
              <option value="">All sources · table only</option>
              {selected?.source_ids.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Metric
            <select
              aria-label="Synthetic database metric"
              value={metric}
              onChange={(e) => {
                setMetric(e.target.value);
                setOffset(0);
                setPage(null);
              }}
            >
              <option value="">All metrics · table only</option>
              {[...numeric, "fatigue_self_report", "exercise_active"].map(
                (m) => (
                  <option key={m}>{m}</option>
                ),
              )}
            </select>
          </label>
        </Panel>
      )}
      {loading && !error && (
        <State kind="loading">Querying local synthetic PostgreSQL.</State>
      )}
      {page && (
        <>
          <Panel title="Query and quality">
            <p>
              {page.total} matching observations · {page.missing} missing ·{" "}
              {page.suspect} suspect
            </p>
            <p>
              Source: {page.source} · page {Math.floor(offset / 100) + 1}. Chart
              and table show this page only. Missing and suspect values are
              gaps; event and ingestion times remain separate.
            </p>
          </Panel>
          {source && chartMetric ? (
            <Trend
              rows={page.items}
              metric={chartMetric}
              evidenceTo="/synthetic-database#observations"
            />
          ) : (
            <p>
              Select one source and a numeric metric for a scope-separated time
              series.
            </p>
          )}
          <Panel title="Database observations">
            <div
              id="observations"
              className="table-wrap"
              style={{ maxWidth: "100%", overflowX: "auto" }}
            >
              <table>
                <thead>
                  <tr>
                    <th>Observation ID</th>
                    <th>UTC event time</th>
                    <th>UTC ingestion time</th>
                    <th>Metric</th>
                    <th>Measurement</th>
                    <th>Scope</th>
                    <th>Quality</th>
                    <th>Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((o) => (
                    <tr key={o.observation_id}>
                      <td>{o.observation_id}</td>
                      <td>{utc(o.timestamp)}</td>
                      <td>{o.ingested_at ? utc(o.ingested_at) : "Unknown"}</td>
                      <td>{o.metric}</td>
                      <td>
                        <ObservationValue observation={o} />
                      </td>
                      <td>
                        {o.scope.kind} ·{" "}
                        {o.scope.kind === "astronaut"
                          ? o.scope.astronaut_id
                          : o.scope.kind === "compartment"
                            ? o.scope.compartment_id
                            : o.scope.mission_id}
                      </td>
                      <td>
                        {o.quality.status} {o.quality.reason_codes.join(", ")}
                      </td>
                      <td>
                        {o.provenance.source_id} · {o.provenance.origin} ·{" "}
                        {o.provenance.simulation?.scenario_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!page.items.length && (
              <State kind="empty">
                No matching persisted synthetic records.
              </State>
            )}
            <button
              disabled={offset === 0}
              onClick={() => setOffset((x) => Math.max(0, x - 100))}
            >
              Previous database page
            </button>
            <button
              disabled={offset + page.items.length >= page.total}
              onClick={() => setOffset((x) => x + 100)}
            >
              Next database page
            </button>
          </Panel>
        </>
      )}
    </>
  );
}
