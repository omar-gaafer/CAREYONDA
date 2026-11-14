import type { useInvestigations } from "./application";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { InvestigationCase } from "../../contracts/investigation";
import { crew } from "../../testing/observations";
import { PageIntro, Panel, Badge, State, utc } from "../../shared/ui";
import {
  AbstentionNotice,
  EvidenceDetailPanel,
  EvidenceReference,
  HypothesisRankList,
  InvestigationStatusBadge,
  InvestigationTimeline,
  QualityLimitationPanel,
  ReasoningProvenancePanel,
  UncertaintyPanel,
} from "../../shared/investigation/components";
export function Intelligence({
  cases,
  crewId,
  hours,
  apiControls,
}: {
  cases: InvestigationCase[];
  crewId: string;
  hours: number;
  apiControls?: ReturnType<typeof useInvestigations>;
}) {
  const [params, setParams] = useSearchParams(),
    [evidence, setEvidence] = useState<string | null>(null);
  const [presetId, setPresetId] = useState("");
  const presets =
    apiControls?.presets.filter(
      (p) => crewId === "all" || p.current.astronaut_id === crewId,
    ) ?? [];
  const preset =
    presets.find((p) => p.current.sample_id === presetId) ?? presets[0];
  const available = cases.filter(
    (c) => crewId === "all" || c.context.astronaut_id === crewId,
  );
  const requested = params.get("investigation");
  const item = requested
    ? available.find((c) => c.result.investigation_id === requested)
    : apiControls
      ? available.at(-1)
      : available[0];
  const select = (id: string) => {
    setParams({ investigation: id });
    setEvidence(null);
  };
  return (
    <>
      <PageIntro title="AI Intelligence">
        Investigate hypotheses and inspect supporting evidence.
      </PageIntro>
      <div className="notice">
        <Badge>SYNTHETIC INVESTIGATIONS</Badge> Rank indicates relative
        compatibility, not medical probability.
      </div>
      <details className="technical-details">
        <summary>About this analysis</summary>
        <p>
          {apiControls
            ? "Configured synthetic windows are submitted to the local M2 engine."
            : "These are precomputed synthetic M2 results."}
        </p>
        <p>
          The global {hours}-hour filter does not trim investigation evidence.
          Each result retains its full current and reference windows.
        </p>
      </details>
      {apiControls && (
        <Panel title="Investigation context">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (preset) {
                setParams({});
                setEvidence(null);
                void apiControls.submit(preset);
              }
            }}
          >
            <label>
              Configured synthetic windows
              <select
                aria-label="Configured synthetic windows"
                value={preset?.current.sample_id ?? ""}
                onChange={(e) => setPresetId(e.target.value)}
              >
                {presets.map((p) => (
                  <option key={p.current.sample_id} value={p.current.sample_id}>
                    {p.title} · {p.current.astronaut_id}
                  </option>
                ))}
              </select>
            </label>
            <button disabled={!preset || apiControls.submitting}>
              {apiControls.submitting ? "Analyzing…" : "Submit investigation"}
            </button>
          </form>
          {apiControls.submissionError && (
            <p role="alert">
              Unable to load results. Any displayed result is from an earlier
              successful submission.
            </p>
          )}
        </Panel>
      )}
      {!available.length ? (
        <State kind="empty">
          No synthetic investigations for the selected crew.
        </State>
      ) : !item ? (
        <State kind="unavailable">
          This investigation is unavailable in the selected crew context.{" "}
          <button
            onClick={() => {
              setParams({});
              setEvidence(null);
            }}
          >
            Show available investigations
          </button>
        </State>
      ) : (
        <>
          <div className="filter-bar">
            <label>
              Investigation
              <select
                value={item.result.investigation_id}
                onChange={(e) => select(e.target.value)}
              >
                {available.map((c) => (
                  <option
                    key={c.result.investigation_id}
                    value={c.result.investigation_id}
                  >
                    {c.title} · {c.context.astronaut_id}
                  </option>
                ))}
              </select>
            </label>
            <InvestigationStatusBadge result={item.result} />
            <Link
              className="text-link"
              to={`/incidents?investigation=${item.result.investigation_id}`}
            >
              Open associated incident
            </Link>
          </div>
          <div
            className="investigation-summary-strip"
            aria-label="Investigation summary"
          >
            <div>
              <small>ASSESSMENT</small>
              <strong>Synthetic research</strong>
            </div>
            <div>
              <small>RANKING</small>
              <strong>Relative compatibility</strong>
            </div>
            <div>
              <small>SAFETY</small>
              <strong>Not evaluated</strong>
            </div>
          </div>
          <nav className="section-links" aria-label="Investigation sections">
            <a href="#investigation-context">Context</a>
            <a href="#hypothesis-evidence">Hypotheses & evidence</a>
            <a href="#reasoning-provenance">Provenance</a>
            <a href="#complete-lineage">Complete lineage</a>
          </nav>
          <div id="investigation-context">
            <Panel title="Investigation overview">
              <div className="investigation-overview">
                <div>
                  <small>Selected astronaut</small>
                  <strong>
                    {crew.find((c) => c.id === item.context.astronaut_id)
                      ?.name ?? item.context.astronaut_id}
                  </strong>
                </div>
                <div>
                  <small>Mission / habitat</small>
                  <strong>
                    {item.context.mission_id} / {item.context.spacecraft_id}
                  </strong>
                </div>
                <div>
                  <small>Current event window · exclusive start</small>
                  <strong>
                    (
                    {utc(
                      new Date(
                        Date.parse(item.result.timestamp) -
                          item.result.window_seconds * 1000,
                      ).toISOString(),
                    )}
                    , {utc(item.result.timestamp)}]
                  </strong>
                </div>
                <div>
                  <small>Reference event window · exclusive start</small>
                  <strong>
                    (
                    {utc(
                      new Date(
                        Date.parse(item.result.reference_timestamp) -
                          item.result.window_seconds * 1000,
                      ).toISOString(),
                    )}
                    , {utc(item.result.reference_timestamp)}]
                  </strong>
                </div>
                <div>
                  <small>Evidence availability</small>
                  <strong>
                    {item.result.observation_ids.length} current /{" "}
                    {item.result.reference_observation_ids.length} reference IDs
                  </strong>
                </div>
                <div>
                  <small>Quality limitations</small>
                  <strong>
                    {item.result.quality_issues.length} evaluated non-valid
                    records
                  </strong>
                </div>
              </div>
            </Panel>
          </div>
          <AbstentionNotice result={item.result} />
          <p className="window-note">
            Human review required. This investigation does not establish safety.
          </p>
          {evidence && (
            <EvidenceDetailPanel
              key={`${item.result.investigation_id}-${evidence}`}
              observation={item.observations.find(
                (o) => o.observation_id === evidence,
              )}
              onClose={() => setEvidence(null)}
            />
          )}
          <div id="hypothesis-evidence">
            <HypothesisRankList result={item.result} onInspect={setEvidence} />
          </div>
          <div className="two-columns investigation-columns">
            <QualityLimitationPanel
              result={item.result}
              onInspect={setEvidence}
            />
            <div id="reasoning-provenance">
              <ReasoningProvenancePanel item={item} />
            </div>
            <UncertaintyPanel items={item.result.uncertainty} />
            <InvestigationTimeline item={item} />
          </div>
          <div id="complete-lineage">
            <Panel title="Complete window lineage">
              <p>
                Includes excluded or contextual observations that need not
                support a hypothesis.
              </p>
              <h3>Current observations</h3>
              {item.result.observation_ids.map((id) => (
                <EvidenceReference id={id} key={id} onInspect={setEvidence} />
              ))}
              <h3>Reference observations</h3>
              {item.result.reference_observation_ids.map((id) => (
                <EvidenceReference id={id} key={id} onInspect={setEvidence} />
              ))}
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
