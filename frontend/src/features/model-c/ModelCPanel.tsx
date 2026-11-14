import { useEffect, useMemo, useRef, useState } from "react";
import {
  fatigueCategories,
  MAX_ASSESSMENT_DAYS,
  type CategoricalIndicator,
  type FatigueCategory,
  type ModelCResponse,
  type NumericIndicator,
} from "../../contracts/model-c";
import {
  createModelCClient,
  ModelCError,
  type ModelCClient,
} from "../../infrastructure/model-c";
import { Badge, PageIntro, Panel } from "../../shared/ui";
import {
  explainReason,
  validateDraft,
  type DraftIssue,
  type EntryDraft,
} from "./application";

const fatigueLabel: Record<FatigueCategory, string> = {
  rested: "Rested",
  tired: "Tired",
  very_tired: "Very tired",
};
// Server times may carry milliseconds; show whole seconds in UTC consistently.
const stamp = (value: string) =>
  new Date(value).toISOString().slice(0, 19).replace("T", " ") + " UTC";
const round = (value: number | null | undefined, digits = 3) =>
  value === null || value === undefined
    ? "—"
    : Number(value.toPrecision(digits)).toString();
const days = (seconds: number) => round(seconds / 86400, 3);
const errorText = (error: ModelCError) =>
  error.kind === "invalid"
    ? `The local API rejected the entries (${error.code ?? "invalid_request"}). Nothing was assessed or stored.`
    : error.kind === "contract"
      ? "The local API returned an unsupported or inconsistent result. Nothing is shown in its place."
      : "The local sleep/fatigue research API is unavailable. Start the backend with app.demo_main (or app.model_c_main); no result is substituted.";

export function ModelCPanel({
  title,
  mode,
  apiUrl = "http://127.0.0.1:8000",
  client: injected,
  now = () => Date.now(),
}: {
  title: string;
  mode: "fixture" | "api";
  apiUrl?: string;
  client?: ModelCClient;
  now?: () => number;
}) {
  const nextKey = useRef(1);
  const generation = useRef(0);
  const [participant, setParticipant] = useState("");
  const [assessmentDays, setAssessmentDays] = useState(3);
  const [drafts, setDrafts] = useState<EntryDraft[]>([]);
  const [showIssues, setShowIssues] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [response, setResponse] = useState<ModelCResponse | null>(null);
  function invalidate() {
    generation.current += 1;
    setResponse(null);
    setFailure("");
    setBusy(false);
  }
  useEffect(() => {
    invalidate();
    return () => {
      generation.current += 1;
    };
  }, [mode, apiUrl, injected]);
  const checked = useMemo(
    () => validateDraft(participant, assessmentDays, drafts, now()),
    [participant, assessmentDays, drafts, now],
  );
  const issuesFor = (key: DraftIssue["key"], field?: DraftIssue["field"]) =>
    showIssues
      ? checked.issues.filter(
          (i) => i.key === key && (!field || i.field === field),
        )
      : [];

  function edit(key: number, change: Partial<EntryDraft>) {
    invalidate();
    setDrafts((rows) =>
      rows.map((r) => (r.key === key ? { ...r, ...change } : r)),
    );
  }
  function addDay() {
    invalidate();
    setDrafts((rows) => {
      const last = rows.at(-1)?.date;
      let date = "";
      if (last && /^\d{4}-\d{2}-\d{2}$/.test(last)) {
        const next = new Date(`${last}T00:00:00Z`);
        next.setUTCDate(next.getUTCDate() + 1);
        date = next.toISOString().slice(0, 10);
      }
      return [
        ...rows,
        { key: nextKey.current++, date, sleep: "", fatigue: "" },
      ];
    });
  }
  function clearSession() {
    invalidate();
    setDrafts([]);
    setParticipant("");
    setResponse(null);
    setFailure("");
    setShowIssues(false);
  }
  async function submit() {
    setShowIssues(true);
    setFailure("");
    setResponse(null);
    if (!checked.submission || mode !== "api") return;
    const requestGeneration = ++generation.current;
    setBusy(true);
    try {
      const client = injected ?? createModelCClient(apiUrl);
      const result = await client.assess(checked.submission);
      if (generation.current === requestGeneration) setResponse(result);
    } catch (error) {
      if (generation.current !== requestGeneration) return;
      setFailure(
        error instanceof ModelCError
          ? errorText(error)
          : "The request could not be prepared. Nothing was sent.",
      );
    } finally {
      if (generation.current === requestGeneration) setBusy(false);
    }
  }

  return (
    <div className="model-c">
      <PageIntro
        eyebrow="Model C · deterministic research prototype · isolation & confinement domain"
        title={title}
      >
        Compare one pseudonymous participant's own daily sleep duration and
        fatigue self-reports with that same participant's earlier entries.
      </PageIntro>
      <div className="workflow-warning" role="note">
        <strong>Local demonstration only — not diagnostic.</strong> Model C is a
        deterministic sleep/fatigue research monitor, not a clinically validated
        isolation or confinement detector. It does not diagnose any condition,
        judge health, recommend treatment or actions, or compute risk, severity
        or probability. It is not suitable for operational astronaut monitoring.
        Only two indicators are supported: sleep duration (hours) and fatigue
        self-report (rested / tired / very tired). Mood, stress, social,
        cognitive and activity data are not supported.
      </div>
      <div className="notice" role="note" aria-label="Data handling">
        <strong>Nothing is saved.</strong> Entries live only in this page's
        memory and are cleared on reload. On submit they are sent once to your
        local API at {apiUrl} and are not stored, logged or shared; no database,
        browser storage, cookies, analytics or external service is used.
        Persistence would need separate approval.
      </div>

      <Panel
        title="1 · Participant and periods"
        action={
          <button type="button" onClick={clearSession}>
            Clear session
          </button>
        }
      >
        <div className="filter-bar">
          <label>
            Pseudonymous participant ID
            <input
              aria-label="Pseudonymous participant ID"
              value={participant}
              disabled={drafts.length > 0}
              onChange={(e) => {
                invalidate();
                setParticipant(e.target.value.trim());
              }}
              placeholder="e.g. crew-x7"
              autoComplete="off"
            />
          </label>
          <label>
            Assessment period (most recent days)
            <select
              aria-label="Assessment period"
              value={assessmentDays}
              onChange={(e) => {
                invalidate();
                setAssessmentDays(Number(e.target.value));
              }}
            >
              {Array.from({ length: MAX_ASSESSMENT_DAYS }, (_, i) => i + 1).map(
                (n) => (
                  <option key={n} value={n}>
                    {n} day{n > 1 ? "s" : ""}
                  </option>
                ),
              )}
            </select>
          </label>
        </div>
        <p className="muted">
          One participant per session. The ID is locked once days are added so
          two people's histories can never be mixed; use “Clear session” to
          start over. Earlier dates form the personal reference period.
        </p>
        {issuesFor("participant").map((i) => (
          <p key={i.message} role="alert">
            {i.message}
          </p>
        ))}
      </Panel>

      <Panel
        title="2 · Daily self-reports"
        action={
          <button type="button" onClick={addDay}>
            Add day
          </button>
        }
      >
        <p className="muted">
          Each date is a self-report anchored at 12:00 UTC. Sleep is the hours
          you report for the 24 hours ending then. Leave a field blank if you
          have no value — it is recorded as “not entered”, never as zero. These
          are self-reports from this form, not wearable or sensor data.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Date (UTC)</th>
                <th>Sleep duration (h)</th>
                <th>Fatigue self-report</th>
                <th>
                  <span className="muted">Remove</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {drafts.map((row, index) => (
                <tr key={row.key}>
                  <td>
                    <input
                      type="date"
                      aria-label={`Date for day ${index + 1}`}
                      value={row.date}
                      onChange={(e) => edit(row.key, { date: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      inputMode="decimal"
                      aria-label={`Sleep hours for day ${index + 1}`}
                      value={row.sleep}
                      placeholder="not entered"
                      onChange={(e) => edit(row.key, { sleep: e.target.value })}
                    />
                  </td>
                  <td>
                    <select
                      aria-label={`Fatigue for day ${index + 1}`}
                      value={row.fatigue}
                      onChange={(e) =>
                        edit(row.key, {
                          fatigue: e.target.value as EntryDraft["fatigue"],
                        })
                      }
                    >
                      <option value="">Not entered</option>
                      {fatigueCategories.map((c) => (
                        <option key={c} value={c}>
                          {fatigueLabel[c]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button
                      type="button"
                      aria-label={`Remove day ${index + 1}`}
                      onClick={() => {
                        invalidate();
                        setDrafts((rows) =>
                          rows.filter((r) => r.key !== row.key),
                        );
                      }}
                    >
                      ×
                    </button>
                  </td>
                  {issuesFor(row.key).length > 0 && (
                    <td role="alert">
                      {issuesFor(row.key)
                        .map((i) => i.message)
                        .join(" ")}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {drafts.length === 0 && (
          <p className="muted">No days entered yet. Use “Add day”.</p>
        )}
        {issuesFor("session").map((i) => (
          <p key={i.message} role="alert">
            {i.message}
          </p>
        ))}
      </Panel>

      <Panel title="3 · Review and submit">
        <p>
          {drafts.length} day{drafts.length === 1 ? "" : "s"} for{" "}
          <strong>{participant || "no participant"}</strong>; assessment period:
          last {assessmentDays} dated day{assessmentDays > 1 ? "s" : ""}.
        </p>
        {mode !== "api" && (
          <p role="status">
            Submission needs “Local API” mode with the backend started from
            app.demo_main (or app.model_c_main). Offline fixture mode does not
            run the analysis and no result is fabricated.
          </p>
        )}
        <button
          type="button"
          onClick={submit}
          disabled={busy || mode !== "api" || drafts.length === 0}
        >
          {busy ? "Assessing…" : "Submit for local analysis"}
        </button>
        {showIssues && checked.issues.length > 0 && (
          <p role="alert">Fix the highlighted entries before submitting.</p>
        )}
        {failure && <p role="alert">{failure}</p>}
      </Panel>

      {response && <ModelCResult response={response} />}
    </div>
  );
}

function Reasons({ codes }: { codes: string[] }) {
  if (!codes.length) return null;
  return (
    <ul aria-label="Abstention reasons">
      {codes.map((c) => (
        <li key={c}>{explainReason(c)}</li>
      ))}
    </ul>
  );
}

export function ModelCResult({ response }: { response: ModelCResponse }) {
  const r = response.result;
  return (
    <section aria-label="Sleep/fatigue research result">
      <Panel title="Result">
        <p>
          Status:{" "}
          <Badge tone={r.status === "assessed" ? "" : "warning"}>
            {r.status.replace("_", " ")}
          </Badge>{" "}
          · participant <strong>{r.subject_id}</strong> · {r.model_id}{" "}
          {r.model_version} · method {r.method_version}
        </p>
        {r.status === "abstained" && (
          <p role="status">
            The analysis abstained: no result is shown because the history did
            not meet the declared requirements.
          </p>
        )}
        <Reasons codes={r.abstention_reasons} />
        <dl className="provenance-list">
          <dt>Reference period</dt>
          <dd>
            {stamp(r.reference_interval.start)} →{" "}
            {stamp(r.reference_interval.end)}
          </dd>
          <dt>Assessment period</dt>
          <dd>
            {stamp(r.assessment_interval.start)} →{" "}
            {stamp(r.assessment_interval.end)}
          </dd>
          <dt>Assessed at</dt>
          <dd>{stamp(r.assessed_at)}</dd>
          <dt>Data origin</dt>
          <dd>
            {r.data_origin} · {response.source} · persistence:{" "}
            {response.persistence}
          </dd>
          <dt>Parameters</dt>
          <dd>
            {r.parameters.parameter_status.replaceAll("_", " ")}:{" "}
            {days(r.parameters.bin_duration_seconds)}-day bins, ≥
            {r.parameters.minimum_occupied_bins} occupied days, ≥
            {r.parameters.minimum_reference_reports} fatigue reports, reference
            at most {days(r.parameters.maximum_reference_age_seconds)} days old.
            These are configurable research defaults, not validated limits.
          </dd>
          <dt>Safety</dt>
          <dd>{r.safety_status.replace("_", " ")}</dd>
        </dl>
        <p className="muted">{response.time_convention}</p>
      </Panel>
      {r.indicators.map((item) =>
        item.kind === "numeric_personal_baseline" ? (
          <SleepResult key={item.indicator} item={item} />
        ) : (
          <FatigueResult key={item.indicator} item={item} />
        ),
      )}
      <Panel title="Limitations">
        <ul>
          {r.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </Panel>
    </section>
  );
}

function Provenance({
  item,
}: {
  item: NumericIndicator | CategoricalIndicator;
}) {
  return (
    <p className="muted">
      Instrument:{" "}
      {item.instrument_kind === "self_report_form"
        ? "self-report form (no physical sensor)"
        : "sensor"}{" "}
      · provenance: {item.evidence_provenance.join(", ") || "none"} · registry
      reporting mode: {item.registry_reporting_mode.replaceAll("_", " ")}
    </p>
  );
}

function SleepResult({ item }: { item: NumericIndicator }) {
  const b = item.baseline;
  return (
    <Panel title="Sleep duration (personal baseline)">
      <p>
        <Badge tone={item.status === "assessed" ? "" : "warning"}>
          {item.status}
        </Badge>{" "}
        Baseline {b.status.replaceAll("_", " ")} · {b.summary.occupied_bins}/
        {b.summary.total_bins} reference days with a valid entry · median{" "}
        {round(b.median_value)} h · raw MAD {round(b.raw_mad)} h
      </p>
      <Reasons codes={item.abstention_reasons} />
      <p className="muted">
        Score = |entry − your reference median| ÷ raw MAD of your daily
        reference values (absolute_deviation_over_raw_mad). It is dimensionless
        and describes distance from your own history only — not a z-score,
        probability, severity or diagnosis. No threshold is applied unless an
        approved research threshold exists (threshold:{" "}
        {item.findings[0]?.policy.threshold_governance ?? "unassessed"}).
      </p>
      <p>
        {item.summary.scored} of {item.summary.findings} assessment-period
        entries scored: {item.summary.above_reference} above,{" "}
        {item.summary.below_reference} below, {item.summary.equal_to_reference}{" "}
        equal to your reference median; median score{" "}
        {round(item.summary.median_raw_mad_score)}.
      </p>
      <div className="table-scroll">
        <table aria-label="Sleep findings">
          <thead>
            <tr>
              <th>Entry</th>
              <th>Value (h)</th>
              <th>Difference from median (h)</th>
              <th>Score</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {item.findings.map((f) => (
              <tr key={f.finding_id}>
                <td>{stamp(f.evidence.observation.timestamp)}</td>
                <td>
                  {f.original_value === null
                    ? "not entered"
                    : round(f.original_value)}
                </td>
                <td>{round(f.signed_deviation)}</td>
                <td>{round(f.raw_mad_score)}</td>
                <td>
                  {f.score_status.replaceAll("_", " ")}
                  {f.abstention_reasons.length > 0 &&
                    ` — ${f.abstention_reasons.map(explainReason).join("; ")}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {b.excluded.length > 0 && (
        <p className="muted">
          Excluded from the reference:{" "}
          {b.excluded
            .map(
              (e) =>
                `${e.evidence.observation.observation_id} (${e.reason_codes.join(", ")})`,
            )
            .join("; ")}
        </p>
      )}
      <Provenance item={item} />
      <p className="muted">{item.explanation}</p>
    </Panel>
  );
}

function FatigueResult({ item }: { item: CategoricalIndicator }) {
  return (
    <Panel title="Fatigue self-report (descriptive counts)">
      <p>
        <Badge tone={item.status === "assessed" ? "" : "warning"}>
          {item.status}
        </Badge>{" "}
        {item.reference_report_ids.length} reference reports ·{" "}
        {item.assessment_report_ids.length} assessment-period reports
      </p>
      <Reasons codes={item.abstention_reasons} />
      <div className="table-scroll">
        <table aria-label="Fatigue counts">
          <thead>
            <tr>
              <th>Category</th>
              <th>Reference period</th>
              <th>Assessment period</th>
            </tr>
          </thead>
          <tbody>
            {item.categories.map((c) => (
              <tr key={c.category}>
                <td>{fatigueLabel[c.category]}</td>
                <td>{c.reference_count}</td>
                <td>{c.assessment_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        Counts of your own self-reports only. No score, distance or threshold is
        applied, and counts are not a diagnosis.
      </p>
      <Provenance item={item} />
    </Panel>
  );
}
