# AI-H3 evaluation protocol and integrity record

Baseline: `7b56152c5bad72dd9446f17c301dcc466b16bd6a`. Python 3.11+; offline synthetic software evaluation only.

Challenge specification SHA-256: `e77a8f5ed47add63aa35fcf9632d564ec7388dfafcb6519397271139e7fca6a2`. This specification was written and hashed before executing the new challenge runner. Expectations must not be revised in response to results. Harness fixes are allowed and must be disclosed; engine changes are out of scope. A mismatch is a finding, not permission to adjust the oracle.

The existing 12 AI-H2 examples and AI_H2_SYNTHETIC_EVALUATION.json are **development tests**: they were used during implementation, including debugging future-availability handling. Their prior “independently specified” wording describes handwritten expectations, not independent held-out validation. The new challenge uses different sleep-duration/fatigue fixtures, timestamps, identifiers, sampling and policy bounds. It is independently specified from documented contracts after the engine freeze, but authored with knowledge of the implementation, not blinded, externally validated, statistically representative or clinically validated. The generic synthetic Model A context constructor is reused and disclosed; no model is fitted or run.

## Frozen fixture semantics

All values and bands are arbitrary software fixtures, not physiological normality or clinical thresholds. Six current samples occur at minutes 1–6. Three reference samples occur at minutes -9 through -7, anchored at -7. Windows are (start,end]. M2 uses the empirical reference range [7,9]; H1 separately uses [6,10]. Fatigue is very_tired unless rested is specified. Policies require persistent_anomaly, except recovery explicitly accepts recovery. Missing replaces sample 3; duplicate repeats sample 1 at the raw input boundary. Wrong mission/subject applies to the reference observations and their reference anchor: M2 permits separate reference contexts, H2 requires exact identity. Future-unavailable delays reference sample 2 until assessment+1 second. Conflicting provenance supplies a second wrapper for reference sample 2 with a different sensor, preserving the raw observation. Model contexts are synthetic contract fixtures, never fitted scores; replay uses a NASA-RR1 spacecraft label, no NASA measurements. Required-model cases must abstain even when raw evidence remains supporting. Stale assessment is event-window end+121 seconds.

## Ablations and metrics

A emits the unchanged M2 investigation. B emits that same investigation plus H1; no ranking fusion. C additionally emits H2 associations; no ranking changes. All receive the same eligible raw observations, anchors and fixed policies. Duplicate raw input is an expected boundary rejection, reported separately and excluded from semantic denominators; it is never silently deduplicated.

Evidence association correctness (exact status and supporting/contradicting ID sets), contradiction handling (exact contradicting sets for cases expecting contradiction), abstention correctness (both positive and negative decisions, including reasons), unsupported directional assertion count (extra H2 support/contradiction IDs beyond the frozen oracle) and embedded provenance completeness (all directional current/reference IDs resolve to embedded snapshots) apply to C only. A/B do not emit prospective H2 associations or embedded H2 trace contracts: report N/A, not zero. M2 native relations/status/rankings are retained for inspection, not reinterpreted as prospective association or clinical accuracy.

Temporal recognition compares H1 labels with the frozen oracle for B/C; A is N/A. Determinism compares complete outputs over repeat calls and reversed observation/evidence order for each configuration, including boundary errors. M2 invariance compares embedded investigations before/after sidecars. Report counts and denominators, not significance or generalization. Provenance resolution is structural completeness, not authentication or truth. Partial supporting IDs may coexist with overall abstention. A missing capability is not an error metric of zero.

## Reproduction

From backend: `PYTHONPATH=. python -m examples.ai_h3_evaluation` emits deterministic JSON. Redirect to a temporary file and compare with AI_H3_RESULTS.json. No downloads, data files, fitted artifacts or new dependencies. Expected-spec digest is pinned in the runner to detect accidental edits. Existing development tests remain regression tests and are counted separately.
