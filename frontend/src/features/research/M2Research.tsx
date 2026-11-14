import { useEffect, useMemo, useRef, useState } from "react";
import { createHttpRepositories } from "../../infrastructure/http";
import type { ApiPreset } from "../../contracts/api";
import type { InvestigationCase } from "../../contracts/investigation";
import { parseInvestigationCases } from "../../contracts/investigation";
import { PageIntro, Panel } from "../../shared/ui";
import {
  HypothesisRankList,
  ReasoningProvenancePanel,
  QualityLimitationPanel,
  UncertaintyPanel,
} from "../../shared/investigation/components";
export function M2Research({ apiUrl }: { apiUrl: string }) {
  const [presets, setPresets] = useState<ApiPreset[]>([]);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<InvestigationCase | null>(null);
  const [inspected, setInspected] = useState<string | null>(null);
  const [status, setStatus] = useState("Loading research contexts");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const repo = useMemo(() => {
    try {
      return createHttpRepositories(apiUrl).investigations;
    } catch {
      return null;
    }
  }, [apiUrl]);
  useEffect(() => {
    const id = ++generation.current;
    setResult(null);
    if (!repo) {
      setStatus("Invalid local API origin");
      return;
    }
    repo
      .presets?.()
      .then((p) => {
        if (id === generation.current) {
          setPresets(p);
          setStatus("");
        }
      })
      .catch(() => {
        if (id === generation.current)
          setStatus("Research API unavailable. No fixture fallback.");
      });
    return () => {
      generation.current++;
    };
  }, [repo]);
  async function submit() {
    if (!repo?.submit || !presets[index]) return;
    const id = ++generation.current;
    setResult(null);
    setBusy(true);
    setStatus("");
    try {
      const payload = await repo.submit(presets[index]);
      const parsed = parseInvestigationCases([payload])[0];
      if (id === generation.current) setResult(parsed);
    } catch {
      if (id === generation.current)
        setStatus(
          "Investigation rejected or unavailable. No result substituted.",
        );
    } finally {
      if (id === generation.current) setBusy(false);
    }
  }
  return (
    <>
      <PageIntro title="M2 synthetic research investigations">
        Actual deterministic engine on server-configured synthetic evidence.
        Separate from NASA replay and authenticated health records. Not a
        clinical assessment.
      </PageIntro>
      <Panel title="Research context">
        <select
          aria-label="M2 research context"
          value={index}
          onChange={(e) => {
            generation.current++;
            setBusy(false);
            setResult(null);
            setIndex(Number(e.target.value));
          }}
        >
          {presets.map((p, i) => (
            <option key={p.current.sample_id} value={i}>
              {p.title}
            </option>
          ))}
        </select>
        <button
          disabled={busy || !presets.length}
          onClick={() => void submit()}
        >
          Run synthetic investigation
        </button>
        <p role="status">{busy ? "Investigating" : status}</p>
      </Panel>
      {result && (
        <>
          <HypothesisRankList result={result.result} onInspect={setInspected} />
          <ReasoningProvenancePanel item={result} />
          <QualityLimitationPanel
            result={result.result}
            onInspect={setInspected}
          />
          <UncertaintyPanel items={result.result.uncertainty} />
          {inspected && (
            <Panel title="Source observation">
              <pre>
                {JSON.stringify(
                  result.observations.find(
                    (o) => o.observation_id === inspected,
                  ) ?? {
                    observation_id: inspected,
                    availability: "not included",
                  },
                  null,
                  2,
                )}
              </pre>
            </Panel>
          )}
        </>
      )}
    </>
  );
}
