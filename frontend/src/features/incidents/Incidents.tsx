import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { InvestigationCase } from "../../contracts/investigation";
import { PageIntro, Panel, Badge, State, utc } from "../../shared/ui";
import { crew } from "../../infrastructure/observations";
import {
  EvidenceDetailPanel,
  EvidenceReference,
  InvestigationStatusBadge,
} from "../../shared/investigation/components";
import { reviewIncident, type IncidentReview } from "./application";
export function Incidents({
  cases,
  crewId,
  reviews,
  onReview,
}: {
  cases: InvestigationCase[];
  crewId: string;
  reviews: Record<string, IncidentReview>;
  onReview: (id: string, next: IncidentReview) => void;
}) {
  const [params, setParams] = useSearchParams(),
    [filter, setFilter] = useState("all"),
    [draft, setDraft] = useState(""),
    [evidence, setEvidence] = useState<string | null>(null);
  const getReview = (id: string): IncidentReview =>
    reviews[id] ?? { status: "open", notes: [] };
  const available = cases.filter(
    (c) =>
      (crewId === "all" || c.context.astronaut_id === crewId) &&
      (filter === "all" ||
        getReview(c.result.investigation_id).status === filter),
  );
  const requested = params.get("investigation"),
    item = requested
      ? available.find((c) => c.result.investigation_id === requested)
      : available[0];
  const select = (id: string) => {
    setParams({ investigation: id });
    setDraft("");
    setEvidence(null);
  };
  const review = item ? getReview(item.result.investigation_id) : null;
  return (
    <>
      <PageIntro
        eyebrow="SYNTHETIC / HUMAN REVIEW WORKFLOW"
        title="Alerts & Incidents"
      >
        Review synthetic incident annotations and associated precomputed
        investigations.
      </PageIntro>
      <div className="notice">
        <Badge tone="amber">DEMO CLASSIFICATIONS</Badge> All incidents have demo
        severity “review exercise” and category “synthetic evidence review.”
        Neither is a clinical severity or safety classification.
      </div>
      <p className="window-note">
        Crew context is shared with other modules. Archived incidents retain
        their original windows; global time filters do not alter them. Notes and
        statuses last only until reload.
      </p>
      <div className="filter-bar">
        <label>
          Workflow status
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setParams({});
              setDraft("");
              setEvidence(null);
            }}
          >
            {["all", "open", "acknowledged", "closed"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      {!available.length ? (
        <State kind="empty">
          No incidents match crew and workflow filters.
        </State>
      ) : (
        <div className="incident-layout">
          <Panel title="Synthetic incidents">
            <div className="incident-list">
              {available.map((c) => (
                <button
                  key={c.result.investigation_id}
                  aria-pressed={item === c}
                  onClick={() => select(c.result.investigation_id)}
                >
                  <strong>{c.title}</strong>
                  <small>
                    {crew.find((p) => p.id === c.context.astronaut_id)?.name} ·{" "}
                    {utc(c.result.timestamp)}
                  </small>
                  <Badge>{getReview(c.result.investigation_id).status}</Badge>
                </button>
              ))}
            </div>
          </Panel>
          {!item || !review ? (
            <State kind="unavailable">
              The linked incident is not available in this crew/status context.
              Select an incident from the list.
            </State>
          ) : (
            <Panel title={item.title}>
              <Badge>SYNTHETIC INCIDENT</Badge>
              <p>
                Severity: review exercise (demo). Category: synthetic evidence
                review.
              </p>
              <p>
                Human workflow:{" "}
                <strong aria-live="polite">{review.status}</strong>
              </p>
              <p>
                Reasoning status:{" "}
                <InvestigationStatusBadge result={item.result} />
              </p>
              <p>
                Safety status: <strong>{item.result.safety_status}</strong>
              </p>
              <div className="incident-actions">
                {review.status === "open" && (
                  <button
                    onClick={() =>
                      onReview(
                        item.result.investigation_id,
                        reviewIncident(review, { type: "acknowledge" }),
                      )
                    }
                  >
                    Acknowledge incident
                  </button>
                )}
                {review.status !== "closed" ? (
                  <button
                    onClick={() =>
                      onReview(
                        item.result.investigation_id,
                        reviewIncident(review, { type: "close" }),
                      )
                    }
                  >
                    Resolve workflow
                  </button>
                ) : (
                  <button
                    onClick={() =>
                      onReview(
                        item.result.investigation_id,
                        reviewIncident(review, { type: "reopen" }),
                      )
                    }
                  >
                    Reopen incident
                  </button>
                )}
                <Link
                  className="primary-link"
                  to={`/ai-intelligence?investigation=${item.result.investigation_id}`}
                >
                  Open investigation
                </Link>
              </div>
              <p className="workflow-warning">
                Closing this workflow does not mean a medical condition was
                resolved, evidence became valid, or safety was established.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  onReview(
                    item.result.investigation_id,
                    reviewIncident(review, {
                      type: "note",
                      text: draft,
                      recordedAt: new Date().toISOString(),
                    }),
                  );
                  setDraft("");
                }}
              >
                <label className="note-label">
                  Manual review note
                  <textarea
                    maxLength={2000}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="Synthetic exercise notes only. Do not enter personal health data."
                  />
                </label>
                <button disabled={!draft.trim()}>Record note</button>
              </form>
              <ul className="finding-list">
                {review.notes.map((note, i) => (
                  <li key={i}>
                    <p>{note.text}</p>
                    <small>Manual session note · {utc(note.recordedAt)}</small>
                  </li>
                ))}
              </ul>
              <h3>Incident evidence</h3>
              {item.result.observation_ids.map((id) => (
                <EvidenceReference key={id} id={id} onInspect={setEvidence} />
              ))}
              {!item.result.observation_ids.length && (
                <p>No current observation IDs supplied.</p>
              )}
              {evidence && (
                <EvidenceDetailPanel
                  key={evidence}
                  observation={item.observations.find(
                    (o) => o.observation_id === evidence,
                  )}
                  onClose={() => setEvidence(null)}
                />
              )}
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
