import type { ApiPreset } from "../../contracts/api";
import { useEffect, useState } from "react";
import {
  parseInvestigationCases,
  type InvestigationCase,
} from "../../contracts/investigation";
import type { InvestigationRepository } from "../../infrastructure/investigations";
export function useInvestigations(repository: InvestigationRepository) {
  const [cases, setCases] = useState<InvestigationCase[]>([]),
    [status, setStatus] = useState<"loading" | "ready" | "error">("loading"),
    [attempt, setAttempt] = useState(0);
  const [presets, setPresets] = useState<ApiPreset[]>([]);
  const [submitting, setSubmitting] = useState(false),
    [submissionError, setSubmissionError] = useState(false);
  useEffect(() => {
    let active = true;
    setStatus("loading");
    Promise.all([
      repository.list(),
      repository.presets?.() ?? Promise.resolve([]),
    ])
      .then(([payload, availablePresets]) => {
        const parsed = parseInvestigationCases(payload);
        if (active) {
          setCases(parsed);
          setPresets(availablePresets);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [repository, attempt]);
  async function submit(preset: ApiPreset) {
    if (!repository.submit) return;
    setSubmitting(true);
    setSubmissionError(false);
    try {
      const result = parseInvestigationCases([
        await repository.submit(preset),
      ])[0];
      setCases((old) => [
        ...old.filter(
          (c) => c.result.investigation_id !== result.result.investigation_id,
        ),
        result,
      ]);
    } catch {
      setSubmissionError(true);
    } finally {
      setSubmitting(false);
    }
  }
  return {
    cases,
    status,
    presets,
    submit,
    submitting,
    submissionError,
    retry: () => setAttempt((n) => n + 1),
  };
}
