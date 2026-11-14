# AI-I3 — Minimal evidence adapter integration

Base: `ed8687a742f706cb35ad5454555fa8eef1a2ff3b` on
`feature/ai-research-assembly`. Four files added; no existing model algorithm,
M2 ranking, M4.2 schema, API, frontend or frozen evaluation file changed.
This is research orchestration, not a clinical or operational inference pipeline.

## Internal Python contract

Module: `app.ai.research.evidence_adapters`.
These are frozen internal dataclasses and typed functions, not a new persisted or
HTTP wire contract. Existing Pydantic input/result contracts are revalidated;
no replacement of H1/H2 or native model schemas is required.

```python
adapt_environmental(context, *, evidence, policy, assessed_at) -> ContextAdaptation
adapt_model_b(finding, *, assessed_at) -> ContextAdaptation
adapt_model_c(request, result, *, policy, assessed_at) -> ContextAdaptation
assess_hybrid(investigation, temporal, *, policy, assessed_at,
              evidence, contexts=()) -> AdaptedHybridAssessment
```

- `ContextAdaptation` retains the full native A/B/C result, optional original C
  request, optional `TemporalSummary`, eligibility flag, reasons and limitations.
- `AdaptedHybridAssessment` retains an unchanged-contract `HybridAssessment` plus
  all contextual adaptations, including rejected/quarantined native results.
- `ResearchAdapterError` indicates original request/result binding failure.
  Validation exceptions remain distinct; no original sensitive values are put in
  custom error messages. No loader, clock, estimator, conversion or fallback is
  invoked by adapters.

## Eligible and rejected paths

| Path | Permitted transformation | Conditions / rejection |
|---|---|---|
| Original numeric evidence → H1 | Existing H1 analysis only | Exact mission/scope, dataset/run/source/sensor/epoch/origin, canonical metric/unit, valid quality, bounded event support, known ingestion by explicit assessment, sufficient fresh data |
| Live A sidecar → H1 model context | Existing A-specific context path | Exact original snapshots and source/scope; H1 retains exclusion reasons; statistical flag never supplies hazard direction |
| Historical A replay | Native contextual result only | Always `historical_replay_not_prospective`; no observation availability rewrite, no astronaut exposure attribution |
| B v2 finding | Native contextual result only | No B context input exists in H1/H2. Keep score, policy, unassessed/abstained status, source context, original evidence, feature/window IDs, imputation and availability intact |
| C sleep observations → H1 | Underlying original observations only | Explicit caller-reviewed sleep/hours numeric policy with matching participant/mission and assessment window; original C request/result identity and current/reference lineage match; H1 filters source, quality and availability independently |
| C scores / baseline / model method | Native contextual information | Never relabel raw-MAD scores as H1 patterns, reference bounds or directional Hybrid evidence |
| C categorical fatigue | Native contextual information | Never encode fatigue counts as numeric H1 evidence; no validated conversion exists |
| Compatible H1 + original M2 → H2 | Existing H2 assessment | Explicit matching policy and original evidence snapshots; source/scope/availability checked by H2 again; M2 snapshot and ranking remain unchanged |
| Wrong mission/subject/source, future/unknown ingestion, mismatched lineage | Exclude, abstain or reject | Never repair identities, invent times, convert units or substitute synthetic results |

The C adapter preserves form-versus-sensor identity via the native request/result;
it does not invent device identities. It does not derive numeric bounds from a
personal baseline. Without an explicit numeric policy, C remains context-only.
C reference observations are retained in native context and excluded from the
assessment window by H1. Future or overlapping support cannot leak into H1 input.

H2 receives only A contexts marked eligible by H1 and **revalidates** them against
original evidence; native B/C outputs remain outer sidecars, never coerced into
`EnvironmentalAnomalyContext`. An eligible model context is provenance, not a vote
for an M2 hypothesis. `assess_hybrid` creates no new hypothesis or ranking.

The B adapter chooses no threshold and never modifies a finding. With the existing
unapproved canonical policy, B stays `unassessed`, flag null. Recorded q95 experiment
metadata remains separate from approval. Missingness/imputation is retained; feature
aggregates and filled values are never reconstructed as new observations.

## Availability and provenance trust boundary

Adapters use original event, support, ingestion, assessment and acquisition fields.
They never call the clock, manufacture acquisition receipts, use event time as an
ingestion proxy, or claim archived data was available during the original mission.
ResearchEvidence and native contracts validate declarations; they do not authenticate
an arbitrary caller or certify instrument provenance. Real deployments still need a
trusted source/receipt authorization boundary. No new API endpoint is provided.
No synthetic fallback exists on validation, source, model or backend failure.

## Synthetic demonstration

`examples.research_adapter_demo` reuses repository-local deterministic fixture
factories (therefore requires the checked-out tests and development dependencies).
It is not a production data provider or model service. Every output is explicitly
labelled synthetic; the B estimator is fake. Some existing A fixtures intentionally
exercise real-origin contract branches with invented values: they are not NASA
measurements or factual telemetry. All fixture arrival/receipt fields are synthetic
scenario declarations, not evidence of real source authorization.

From repository root in the already provisioned compatible environment:

```sh
cd backend
PYTHONPATH=.:.. python -m examples.research_adapter_demo
```

Repository root must be included in PYTHONPATH so the existing simulator package
can be imported; the initial invocation without it failed before completing the demo.
No source-path hack or installed-package change was introduced.

The deterministic output verifies:

1. Temporal `persistent_anomaly` under explicitly arbitrary software-test bounds.
2. Hybrid `supported_by_available_evidence` using compatible original synthetic
   observations and an unchanged M2 investigation.
3. Cross-subject evidence abstains, with zero usable observations.
4. NASA-labelled synthetic historical replay is quarantined.
5. Model B remains `unassessed` and contextual only.
6. C preserves subject, hours and categorical context; a future-support target is
   excluded from temporal input. Compatible sleep data yields `no_pattern`.
7. M2 output remains unchanged.

No clinical meaning attaches to the fixture values, bounds, temporal label or
synthetic hypothesis result. The demonstration supplies no evidence of a common
context between NASA environment and synthetic health records.

## Verification report

Existing isolated CPython 3.12.10 environment used; numerical pins and HTTP overlay
were already provisioned. No packages installed, no artifact loaded and no model
trained. An external verification guard rejects any actual IsolationForest.fit call.

| Check | Result |
|---|---|
| New adapter tests | **26 passed** |
| H1/H2/H3 and adapter regressions | **173 passed** |
| Full relevant backend | **751 passed, 9 skipped, 1 deselected** |
| Synthetic demonstration | Completed; deterministic repeat tested |
| Frozen H3 evaluation | Exact JSON match with unchanged stored result |
| Ruff and formatting | Passed, 110 files checked for formatting |
| Strict mypy including A script and imported demo | Passed, 108 source files |
| Dependency consistency | Passed |
| Whitespace | Passed |

Coverage includes exact source identity fields, mission/subject mismatch, ppm/Pa
rejection, unknown/future ingestion, replay quarantine, B unassessed/abstained states,
feature lineage and imputation retention, C explicit-policy/no-conversion behavior,
C original current/reference lineage, future support, compatible Hybrid reasoning,
M2 invariance and deterministic output.

Nine full-suite skips remain: six B fitting tests disabled by default, original
published B artifact integrity unavailable, optional trusted A artifact replay and
optional NASA CSV validation. The one deselection is the unchanged inherited A
synthetic fitting test. No safety check was removed and no expected result changed.
H3 challenge remains contract testing, not blind/clinical validation.

Reproduction:

```sh
cd backend
PYTHONPATH=.:.. python -m examples.research_adapter_demo
python -m pytest -q tests/integration/test_research_adapters.py
env -u CAREYONDA_RUN_MODEL_B_FIT_TESTS python -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
python -m examples.ai_h3_evaluation > "$H3_TEMP_OUTPUT"
python -m ruff check app tests ../simulator scripts examples/research_adapter_demo.py
python -m ruff format --check app tests ../simulator scripts examples/research_adapter_demo.py
python -m mypy
python -m pip check
git diff --check
```

Set H3_TEMP_OUTPUT to an external temporary file; do not overwrite tracked results.
The no-training guard was local verification infrastructure, not a new package or
repository configuration. No trusted fitted artifact is required by these commands.

## Exact new files and remaining application tasks

- `backend/app/ai/research/evidence_adapters.py`
- `backend/examples/research_adapter_demo.py`
- `backend/tests/integration/test_research_adapters.py`
- `docs/research/AI_I3_EVIDENCE_ADAPTERS.md`

No unrelated worktree changed. Original Model A/B artifacts remain byte-identical.
Remaining application work: source/receipt authorization and provisioning, explicit
B policy approval or acceptance of unassessed outputs, reviewed real-data temporal
conventions, and coherent separately authorized transport/frontend composition.
Model C UI import must include the previously deferred stale-response fix. No part
of AI-I3 authorizes clinical decisions, autonomous action or cross-scope exposure
inference. Scope-safe contextual research evaluation is the stop point.
