import { Drawer } from "../Drawer";
import type {
  Investigation,
  InvestigationCase,
  EvidenceFinding,
} from "../../contracts/investigation";
import type { Observation } from "../../contracts/observation";
import { Badge, Panel, ObservationValue, utc } from "../ui";
export const humanize = (s: string) => s.replaceAll("_", " ");
export function InvestigationStatusBadge({
  result,
}: {
  result: Investigation;
}) {
  return (
    <Badge tone={result.status === "ranked" ? "cyan" : "amber"}>
      {humanize(result.status)}
    </Badge>
  );
}
export function AbstentionNotice({ result }: { result: Investigation }) {
  return (
    <div className="notice" role="status">
      <Badge tone={result.selected_hypothesis ? "cyan" : "amber"}>
        {result.selected_hypothesis ? "PATTERN SELECTED" : "ABSTAINED"}
      </Badge>
      <span>
        {result.selected_hypothesis
          ? `${humanize(result.selected_hypothesis)} · synthetic compatibility only, not a diagnosis.`
          : `No hypothesis selected · ${humanize(result.status)}. Missing or conflicting evidence never establishes safety.`}
      </span>
    </div>
  );
}
export function EvidenceReference({
  id,
  onInspect,
}: {
  id: string;
  onInspect: (id: string) => void;
}) {
  return (
    <button
      className="text-link evidence-reference"
      onClick={() => onInspect(id)}
      aria-label={`Inspect evidence ${id}`}
    >
      {id}
    </button>
  );
}
export function EvidenceDetailPanel({
  observation,
  onClose,
}: {
  observation: Observation | undefined;
  onClose: () => void;
}) {
  return (
    <Drawer label="Evidence inspection" onClose={onClose}>
      <section
        className="evidence-detail"
        aria-label="Investigation evidence details"
      >
        <Panel
          title="Original synthetic observation"
          action={<button onClick={onClose}>Close evidence</button>}
        >
          {!observation ? (
            <p role="alert">
              Evidence unavailable. No substitute measurement is shown.
            </p>
          ) : (
            <>
              <Badge>SYNTHETIC OBSERVATION</Badge>
              <dl>
                <dt>Evidence ID</dt>
                <dd>{observation.observation_id}</dd>
                <dt>Metric</dt>
                <dd>{humanize(observation.metric)}</dd>
                <dt>Measurement</dt>
                <dd>
                  <ObservationValue observation={observation} />
                </dd>
                <dt>Event time</dt>
                <dd>{utc(observation.timestamp)}</dd>
                <dt>Ingestion time</dt>
                <dd>
                  {observation.ingested_at
                    ? utc(observation.ingested_at)
                    : "Not supplied"}
                </dd>
                <dt>Quality / reasons</dt>
                <dd>
                  {observation.quality.status} /{" "}
                  {observation.quality.reason_codes.join(", ") ||
                    "None reported"}
                </dd>
                <dt>Absence reason</dt>
                <dd>
                  {observation.measurement.kind === "unavailable"
                    ? observation.measurement.reason
                    : "Not absent"}
                </dd>
                <dt>Scope</dt>
                <dd>{JSON.stringify(observation.scope)}</dd>
                <dt>Origin / source</dt>
                <dd>
                  {observation.provenance.origin} /{" "}
                  {observation.provenance.source_id}
                </dd>
                <dt>Method / generator</dt>
                <dd>
                  {observation.provenance.method} /{" "}
                  {observation.provenance.simulation?.generator_version ??
                    "Not supplied"}
                </dd>
                <dt>Contract</dt>
                <dd>{observation.schema_version}</dd>
              </dl>
            </>
          )}
        </Panel>
      </section>
    </Drawer>
  );
}
export function QualityLimitationPanel({
  result,
  onInspect,
}: {
  result: Investigation;
  onInspect: (id: string) => void;
}) {
  return (
    <Panel title="Data quality limitations">
      {!result.quality_issues.length ? (
        <p>
          No non-valid observations reported in these windows. This is not a
          safety assessment.
        </p>
      ) : (
        <ul className="finding-list">
          {result.quality_issues.map((q) => (
            <li key={`${q.window}-${q.observation_id}`}>
              <Badge tone="amber">{q.status}</Badge> {q.window} ·{" "}
              {humanize(q.metric)}
              <p>{q.reason_codes.join(", ")}</p>
              <EvidenceReference id={q.observation_id} onInspect={onInspect} />
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
export function UncertaintyPanel({ items }: { items: string[] }) {
  return (
    <Panel title="Uncertainty & limitations">
      <ul className="finding-list">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </Panel>
  );
}
export function ReasoningProvenancePanel({
  item,
}: {
  item: InvestigationCase;
}) {
  return (
    <Panel title="Reasoning provenance">
      <dl className="provenance-list">
        <dt>Origin</dt>
        <dd>
          {item.origin === "synthetic_api"
            ? "Synthetic evidence · computed by local M2 API"
            : "Synthetic, precomputed with local M2 · no live AI"}
        </dd>
        <dt>Investigation</dt>
        <dd>{item.result.investigation_id}</dd>
        <dt>Result contract</dt>
        <dd>{item.result.schema_version}</dd>
        <dt>Engine version</dt>
        <dd>{item.result.engine_version}</dd>
        <dt>Fixture envelope</dt>
        <dd>{item.fixture_version}</dd>
        <dt>Safety status</dt>
        <dd>
          <Badge tone="amber">{item.result.safety_status}</Badge> · not
          evaluated
        </dd>
      </dl>
      <p>
        Reference is a caller-selected empirical comparator, not a clinical
        normal range or validated personalized baseline.
      </p>
    </Panel>
  );
}
export function InvestigationTimeline({ item }: { item: InvestigationCase }) {
  const t = Date.parse(item.result.timestamp);
  return (
    <Panel title="Investigation timeline">
      <Badge>SYNTHETIC STORYBOARD</Badge>
      <ol className="timeline">
        {[
          ["Incident observations", t],
          ["Investigation created", t + 15000],
          ["Evidence review illustrated", t + 30000],
          ["Hypotheses evaluated", t + 45000],
          [
            item.result.selected_hypothesis
              ? "Pattern selected"
              : "Selection abstained",
            t + 60000,
          ],
        ].map(([label, time]) => (
          <li key={label}>
            <span className="event-dot" />
            <div>
              <strong>{label}</strong>
              <small>{utc(new Date(time).toISOString())}</small>
            </div>
          </li>
        ))}
      </ol>
      <p>
        Illustrative timing; these are not actual engine execution or
        human-review audit events.
      </p>
    </Panel>
  );
}
function Findings({
  title,
  findings,
  onInspect,
}: {
  title: string;
  findings: EvidenceFinding[];
  onInspect: (id: string) => void;
}) {
  return (
    <section className="finding-group">
      <h3>
        {title} <Badge>{findings.length}</Badge>
      </h3>
      {!findings.length ? (
        <p className="muted">None reported.</p>
      ) : (
        <ul className="finding-list">
          {findings.map((f, i) => (
            <li key={`${f.metric}-${i}`}>
              <strong>
                {humanize(f.metric)} · {humanize(f.relation)}
              </strong>
              <p>{f.explanation}</p>
              {f.observed_value !== null && (
                <p>
                  Window value: {f.observed_value} {f.unit}
                </p>
              )}
              {f.reference_minimum !== null && (
                <p>
                  Empirical reference: {f.reference_minimum}–
                  {f.reference_maximum} {f.unit}
                </p>
              )}
              <div>
                <small>Current evidence</small>
                {f.observation_ids.length ? (
                  f.observation_ids.map((id) => (
                    <EvidenceReference key={id} id={id} onInspect={onInspect} />
                  ))
                ) : (
                  <p>No current observation IDs supplied.</p>
                )}
                <small>Reference evidence</small>
                {f.reference_observation_ids.length ? (
                  f.reference_observation_ids.map((id) => (
                    <EvidenceReference key={id} id={id} onInspect={onInspect} />
                  ))
                ) : (
                  <p>No reference IDs supplied for this finding.</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
export function HypothesisRankList({
  result,
  onInspect,
}: {
  result: Investigation;
  onInspect: (id: string) => void;
}) {
  return (
    <Panel title="Ranked synthetic hypotheses">
      <p className="muted">
        Relative compatibility order, not probabilities. Equal ranks remain
        ties.
      </p>
      <div className="hypothesis-list">
        {result.hypotheses.map((h) => (
          <details
            key={h.hypothesis_id}
            open={h.hypothesis_id === result.selected_hypothesis}
          >
            <summary>
              <span className="rank-number">{h.rank}</span>
              <strong>{humanize(h.hypothesis_id)}</strong>
              <Badge>{h.compatibility}</Badge>
              {h.hypothesis_id === result.selected_hypothesis && (
                <Badge tone="cyan">SELECTED PATTERN</Badge>
              )}
            </summary>
            <div className="hypothesis-body">
              <p>{h.explanation}</p>
              <p className="muted">
                Expected relations:{" "}
                {Object.entries(h.expected_relations)
                  .map(([m, r]) => `${humanize(m)}: ${humanize(r)}`)
                  .join("; ")}
              </p>
              <Findings
                title="Supporting evidence"
                findings={h.supporting_evidence}
                onInspect={onInspect}
              />
              <Findings
                title="Contradicting evidence"
                findings={h.contradictory_evidence}
                onInspect={onInspect}
              />
              <Findings
                title="Missing evidence"
                findings={h.missing_evidence}
                onInspect={onInspect}
              />
              <h3>Hypothesis limitations</h3>
              <ul>
                {h.uncertainty.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>
    </Panel>
  );
}
