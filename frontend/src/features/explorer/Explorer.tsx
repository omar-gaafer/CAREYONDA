import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { metrics, type Observation } from "../../contracts/observation";
import {
  Badge,
  ObservationValue,
  PageIntro,
  Panel,
  State,
  utc,
} from "../../shared/ui";
export function Explorer({ rows }: { rows: Observation[] }) {
  const [params, setParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const metric = params.get("metric") ?? "all",
    quality = params.get("quality") ?? "all";
  const filtered = rows
    .filter(
      (o) =>
        (metric === "all" || o.metric === metric) &&
        (quality === "all" ||
          (quality === "limited"
            ? o.quality.status !== "valid"
            : o.quality.status === quality)),
    )
    .sort(
      (a, b) =>
        b.timestamp.localeCompare(a.timestamp) ||
        a.observation_id.localeCompare(b.observation_id),
    );
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(filtered.length / 15) - 1),
  );
  const selected = rows.find((o) => o.observation_id === selectedId);
  const change = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    setParams(next);
    setPage(0);
    setSelectedId(null);
  };
  return (
    <>
      <PageIntro
        eyebrow="RESEARCH / TRACEABLE OBSERVATIONS"
        title="Data Explorer"
      >
        Inspect original synthetic measurements, quality flags, and source
        provenance.
      </PageIntro>
      <div className="filter-bar">
        <label>
          Metric
          <select
            value={metric}
            onChange={(e) => change("metric", e.target.value)}
          >
            <option value="all">All metrics</option>
            {Object.entries(metrics).map(([key, d]) => (
              <option key={key} value={key}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Quality
          <select
            value={quality}
            onChange={(e) => change("quality", e.target.value)}
          >
            {[
              "all",
              "limited",
              "valid",
              "suspect",
              "invalid",
              "missing",
              "unavailable",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <span>{filtered.length} observations · synthetic</span>
      </div>
      <Panel title="Observation evidence">
        {!filtered.length ? (
          <State kind="empty">
            No evidence matches these filters. Change metric, crew, quality, or
            time range.
          </State>
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Event time (UTC)</th>
                    <th>Metric / scope</th>
                    <th>Measurement</th>
                    <th>Quality</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered
                    .slice(currentPage * 15, currentPage * 15 + 15)
                    .map((o) => (
                      <tr key={o.observation_id}>
                        <td>{utc(o.timestamp)}</td>
                        <td>
                          {metrics[o.metric].label}
                          <small>
                            {o.scope.kind === "astronaut"
                              ? o.scope.astronaut_id
                              : "HABITAT-01"}
                          </small>
                        </td>
                        <td>
                          <ObservationValue observation={o} />
                        </td>
                        <td>
                          <Badge
                            tone={o.quality.status === "valid" ? "" : "amber"}
                          >
                            {o.quality.status}
                          </Badge>
                          <small>
                            {o.quality.reason_codes.join(", ") ||
                              "No limitations reported"}
                          </small>
                        </td>
                        <td>
                          <button
                            className="text-link"
                            aria-label={`Inspect ${o.observation_id}`}
                            onClick={() => setSelectedId(o.observation_id)}
                          >
                            Inspect provenance
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button
                disabled={currentPage === 0}
                onClick={() => setPage(currentPage - 1)}
              >
                Previous
              </button>
              <span>
                Page {currentPage + 1} of {Math.ceil(filtered.length / 15)}
              </span>
              <button
                disabled={(currentPage + 1) * 15 >= filtered.length}
                onClick={() => setPage(currentPage + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}
      </Panel>
      {selected && (
        <section
          className="evidence-detail"
          aria-label="Evidence details"
          aria-live="polite"
        >
          <Panel
            title="Evidence & provenance"
            action={
              <button onClick={() => setSelectedId(null)}>Close details</button>
            }
          >
            <Badge>SYNTHETIC</Badge>
            <dl>
              <dt>Evidence identifier</dt>
              <dd>{selected.observation_id}</dd>
              <dt>Event time</dt>
              <dd>{utc(selected.timestamp)}</dd>
              <dt>Ingestion time</dt>
              <dd>
                {selected.ingested_at
                  ? utc(selected.ingested_at)
                  : "Not supplied"}
              </dd>
              <dt>Measurement</dt>
              <dd>
                <ObservationValue observation={selected} />
              </dd>
              {selected.measurement.kind === "unavailable" && (
                <>
                  <dt>Absence reason</dt>
                  <dd>{selected.measurement.reason}</dd>
                </>
              )}
              <dt>Quality reasons</dt>
              <dd>
                {selected.quality.reason_codes.join(", ") ||
                  "None reported; not a safety determination"}
              </dd>
              <dt>Origin / source</dt>
              <dd>
                {selected.provenance.origin} / {selected.provenance.source_id}
              </dd>
              <dt>Generation method</dt>
              <dd>{selected.provenance.method}</dd>
              <dt>Generator / seed</dt>
              <dd>
                {selected.provenance.simulation?.generator_version ??
                  "Not applicable"}{" "}
                / {selected.provenance.simulation?.seed ?? "Not applicable"}
              </dd>
              <dt>Parent observations</dt>
              <dd>None · original synthetic fixture</dd>
              <dt>Contract version</dt>
              <dd>{selected.schema_version}</dd>
            </dl>
          </Panel>
        </section>
      )}
    </>
  );
}
