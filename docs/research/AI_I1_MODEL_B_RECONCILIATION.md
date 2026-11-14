# AI-I1 — Model B canonical contract reconciliation

Status: implemented for owner review; **no threshold policy is approved or selected**.
No commits, merges, pushes, training, or artifact deserialization were performed.
The default scored result is `unassessed`, never implicitly `not_flagged`.

## Source inventory and provenance

This isolated branch starts at the shared application checkpoint
`1ebdd03a8b29239742074e3ac0bff247d8a5785b`.
Published source reviewed: `feature/model-b-health-anomaly` at
`a9b69d41398f69506f63ac93db0a5f5536400cfe`, including its changes after
`28db72b308481cab43c833f67fc56c0d0b22c67b`.
Local enhanced source reviewed read-only: `feature/model-b-integration`, committed
HEAD `1ebdd03`; HEAD does **not** identify its unpublished Model B implementation.
The local source was neither modified nor imported wholesale. Its contract informed
the new v2 contract; no local fitted artifacts or evaluation outputs were copied.

Ahmed's `ai/anomaly.py` and `ai/baseline.py` are copied byte-for-byte from the
published commit. Published simulator research utilities, three test files and
six historical reports are included so their fixes are reproducible. Historical
reports describe their original work and are not evidence of verification here.
This document takes precedence for the current contract and verification status.
No published research datasets, measurements, artifacts or results JSON were copied.

## Published/local reconciliation

| Concern | Published a9b69d4 | Unpublished local enhancement | Canonical v2 decision |
|---|---|---|---|
| Feature schema | External schema, generic array/mapping inference | Validated 16-element input | Exact ordered 16 elements and units; no domain dependency on feature-layer classes |
| Predictors | HR latest/missing/mean; CO2 latest/missing/mean; sleep latest/missing/mean; fatigue latest/missing; delay latest/missing/mean; exercise latest/missing | Same order | Same order, labels/IDs outside predictors |
| Units | bpm; Pa; h; categorical/boolean and missingness dimensionless; delay s | Same | Exact match; NASA concentration ppm rejected as pressure Pa |
| Encoding | Fatigue rested/tired/very_tired = 0/1/2; exercise false/true = 0/1 | Same | Validate codes; these ordinal values are synthetic conventions |
| Preprocessing | Training median imputer, no scaling | Training medians; fail entirely missing training column; explicit imputation | Inject already fitted medians, preserve nulls and imputed-feature/value slots; no fitting |
| Estimator | IF 200 trees, max_samples 256, max_features 1, no bootstrap, contamination auto, one job, seed 42 by default | Same defaults; explicit policy; effective sample bound | Original estimator unchanged; versioned metadata records configuration; injected `score_samples` interface |
| Orientation | `-score_samples` | Same | Same, higher statistical atypicality; never probability |
| Production decision | Strict `score > -offset_` | Training quantile with `method=higher`, strict `>` | Separate named policy, no default approval |
| Research decision | Calibration threshold, inclusive `>=` | Not the local training quantile | Separate named policy, no implicit adoption |
| Scope | Not in inference output | SampleAnchor astronaut/mission/spacecraft/compartment | Contract-owned ModelBContext plus expected server binding |
| Time | Dataset event-time; no validated assessment/availability envelope | Retrospective event-time declaration | Original event, explicit assessment, optional acquisition and reference; source ingestion stays in original observations |
| Availability | No inference gate | Retrospective-only | Replay requires matching injected acquisition receipt; prospective requires declared ingestion by assessment; no timestamp defaults |
| Lineage | Dataset loader pools episode/sample metadata | Per-feature and window IDs | Full original ResearchEvidence plus per-feature IDs; regenerate M1.2 features and compare all values/lineage before scoring |
| Missingness | Can median-impute wholly absent input without abstention | All six metric families absent => abstain | Explicit all-missing abstention; partial imputation is visible |
| Outcomes | Array scores and estimator flags | flagged/not_flagged/abstained | flagged/not_flagged/unassessed/abstained, internally validated |
| Persistence | Raw pickle API | Opt-in manifest-pinned loader | Bytes-only hash, metadata and exact-runtime checks; no loader or persistence writer added |
| Dependencies | Numerical packages undeclared | Pinned optional Model B extra | Direct optional NumPy/SciPy/sklearn/joblib pins plus existing compatible resolution |
| Tests | New dedicated research tests; missing external manifest; fitting tests | Rich tests, some training/artifact serialization | Self-contained manifest fixture; fake estimator tests; fitting tests explicitly opt-in |

## Contract and application boundaries

`app/schemas/model_b.py` owns v2 inputs, metadata, policy and findings. This is a
**new major version**, not a silent reinterpretation of unpublished v1 findings.
No automatic v1 migration exists: original evidence and actual acquisition metadata
must be supplied, not inferred from old pooled IDs or event timestamps.

`ModelBService.assess(ModelBInput) -> ModelBFinding` accepts an explicit
`ModelBBinding`, optional verified metadata/scorer pair, acquisition receipts and an
optional policy through its constructor. No transport endpoint or frontend is added.
Scorers expose the existing sklearn `score_samples` orientation on an already
median-imputed 16-column row. The service negates it once. It never calls `fit`,
`predict`, a loader, a network service or a synthetic fallback.

Inputs preserve full original observations, source/sensor identities, dataset/run,
mission, astronaut, spacecraft, compartment, support intervals and sample event time.
The unchanged M1.2 extractor reconstructs the `(event-300s, event]` features. Any
value, ID, ordering, scope, origin or lineage mismatch fails before inference.
Suspect/invalid readings remain in evidence but cannot become observed features.

Replay acquisition is matched against independently injected receipts for the
specific dataset-manifest digest, timestamp and reference. Receipt creation is not
part of this service. Unknown acquisition yields abstention. Acquisition must be
between original event and explicit assessment. Original source availability stays
`unknown`; acquisition never replaces NASA/source ingestion. Replay outputs carry
`careyonda_replay` and cannot be relabelled `declared_source_stream`.
Prospective research accepts only original evidence with ingestion/support available
by assessment. These are caller-declared research timestamps, **not independent
source authentication**. Synthetic simulator ingestion is not real astronaut data.
Neither mode establishes live spacecraft exposure or a common context with NASA.

## Threshold policy decision — BLOCKED pending owner review

| Name | Derivation | Equality | Status |
|---|---|---|---|
| `published_estimator_offset` | Negative offset of the exact fitted estimator | Not flagged (`>`) | Alternative only |
| `local_training_quantile` | Explicit training-baseline quantile, NumPy `higher` convention | Not flagged (`>`) | Alternative only |
| `exploratory_calibration` | Separately documented calibration procedure | Flagged (`>=`) | Alternative only; exploratory results not approved |

All candidates require artifact digest and derivation-manifest digest/reference.
The local quantile must be explicit. No cutoff, quantile, alert budget or approval
is chosen here. A policy with no approval reference produces a score but leaves the
decision `unassessed` with null flag. Tests use clearly synthetic approval references
solely to verify below/equal/above semantics. An approval string is not software-
verified authority: a future trusted composition root must allow only reviewed
policies. HTTP callers must never set policy approval, trust pins or receipt lists.

Recommendation: keep no-policy/unassessed until the owner reviews the artifact,
threshold derivation and synthetic evaluation assumptions. Preserve whichever named
policy is approved without equating an estimator offset, training quantile and
validation-calibrated cutoff. No clinical threshold is introduced.

## Artifact trust and dependencies

`verify_model_b_artifact` requires trusted-local opt-in, independent artifact and
metadata SHA-256 pins, exact runtime match, exact schema/units and IF parameter
metadata. It verifies supplied bytes only, never deserializes. Hashes establish
consistency, not publisher authenticity. No original baseline Model B artifact was
available or substituted. Fake estimators are for tests only, not runtime fallback.
Before real scoring, a separately authorized loader must consume those verified
bytes, inspect the actual fitted estimator/preprocessor and match medians,
configuration, feature count and score orientation before injecting it. The new
metadata format does not claim compatibility with Ahmed's raw pickle or the local
v1 manifest format without an explicit reviewed migration.

Optional direct dependencies: numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1,
joblib 1.6.0. Python 3.12.10 is the verified runtime; project syntax targets 3.11.
`requirements-model-b-resolved.txt` reuses the existing combined numerical/backend
resolution rather than changing other models' pins. No packages were installed.
These packages were already provisioned. Numerical package metadata supports the
project minimum; other Python/platform combinations were not newly tested.

The published eight mypy findings are repaired using narrow documented untyped-
import exceptions for sklearn, a distinct dictionary-branch accumulator, explicitly
integer NumPy index arrays and a typed mixed-input fixture. Statistical behavior
is unchanged. Markdown trailing spaces were removed in imported documentation.

## Reproducible verification without fitting

From `backend`, using the previously approved environment:

```sh
python -m pytest -q tests/unit/test_model_b_reconciliation.py tests/unit/test_model_b_inference_contract.py tests/unit/test_model_b_challenger_experiments.py tests/unit/test_benign_exercise_control.py
python -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
python -m ruff check app tests ../simulator
python -m ruff format --check app tests ../simulator
python -m mypy
python -m pip check
git diff --check
```

Six published tests that fit estimators require a separate explicit
`CAREYONDA_RUN_MODEL_B_FIT_TESTS=1` opt-in. It was **not set** here. The original
Model B baseline-artifact integrity test stays skipped because no baseline artifact
was located. The self-contained manifest test writes only synthetic feature-order
metadata under pytest's temporary directory; it is not a replacement dataset or
verification of the absent Part 3 training manifest.

During verification a temporary external pytest guard denied every actual IF `fit`
call. The first full run stopped one inherited Model A synthetic fitting test
before fitting (492 passed, 9 skipped, 1 guard failure). That unchanged test is
excluded by the final command above. Real NASA/artifact opt-in tests remain skipped.
No Model A test/source or other model contract was modified to make this pass.
The temporary HTTP dependency overlay reuses existing packages; it is not an install
or a fresh dependency-resolution claim.

## Evaluation and integration limitations

The historical reports do not establish independent model validation. Their source
experiment datasets/results are not published with this reconciliation. No prior
metrics were reproduced, challenger selected or final-test data opened. Benign
exercise controls use hand-set response assumptions; activity can be statistically
atypical without illness. Statistical scores are not diagnoses, probabilities,
severity, calibrated confidence or evidence of a causal mechanism.

For hybrid integration: approve this v2 contract; obtain the trusted fitted model
and provenance; select a reviewed named policy (or explicitly accept unassessed);
add an independently reviewed loader/binding; resolve raw evidence availability,
subject/mission/source and bounded supports; then design a model-B-specific or
model-neutral context adapter. AI-H1/H2 currently accepts Model A contexts only.
No Model B score may be coerced into EnvironmentalAnomalyContext or turned into
M2 directional support. NASA ppm and synthetic Pa, real and synthetic origins,
retrospective and prospective evidence remain separate. M2/M4.2, Model A/C,
AI-H1/H2/H3, API and frontend files are unchanged.

## Final verification results

- Dedicated Model B: **74 passed, 7 skipped** (51 new canonical contract tests).
- Full relevant backend, with the external no-fitting guard: **492 passed,
  9 skipped, 1 deselected**. The deselected test is the unchanged Model A fitting
  test named above. Nine skips comprise six explicit fitting opt-ins, one absent
  original Model B artifact and two real NASA/artifact opt-ins.
- Ruff lint and formatting: passed; 83 Python files formatted.
- Strict mypy: passed on 83 source files, including all imported Model B research
  and test modules. None of the eight published findings remain.
- Installed numerical versions satisfy every new direct pin; `pip check` found no
  broken requirements. No installation or Windows resolver run occurred.
- `git diff --check` and independent whitespace inspection of all 21 changed/new
  files: passed. Nothing staged, committed or pushed.
- Seven pre-existing worktrees retain identical tracked/unignored source hashes,
  status, branch and HEAD. Four trusted Model A artifact files retain their hashes.
- Ahmed's estimator and trainer match the published commit byte-for-byte.
- Protected baseline API/application/frontend and M2/M4.2 files remain identical
  to starting HEAD. Model A/C and Hybrid branches were not modified.

## Exact changed-file inventory

Paths below are relative to the reconciliation worktree. New source is untracked;
modified tracked files are unstaged. The inventory includes this document.

- `backend/app/ai/anomaly.py`
- `backend/app/ai/baseline.py`
- `backend/app/ai/model_b_anomaly.py`
- `backend/app/schemas/model_b.py`
- `backend/app/storage/model_b_store.py`
- `backend/pyproject.toml`
- `backend/requirements-model-b-resolved.txt`
- `backend/tests/unit/test_benign_exercise_control.py`
- `backend/tests/unit/test_model_b_challenger_experiments.py`
- `backend/tests/unit/test_model_b_inference_contract.py`
- `backend/tests/unit/test_model_b_reconciliation.py`
- `docs/architecture/MODEL_B_AUDIT.md`
- `docs/architecture/MODEL_B_BENIGN_EXERCISE_CONTROL.md`
- `docs/architecture/MODEL_B_VALIDATION_PROTOCOL.md`
- `docs/research/AI_I1_MODEL_B_RECONCILIATION.md`
- `docs/research/MODEL_B_PART3_CHALLENGER_EXPERIMENTS.md`
- `docs/research/MODEL_B_PART4_CANDIDATE_EVALUATION_AND_SELECTION.md`
- `docs/research/MODEL_B_PART5_FINAL_DELIVERY_REPORT.md`
- `simulator/research/__init__.py`
- `simulator/research/benign_exercise_control.py`
- `simulator/research/model_b_challenger_experiments.py`

## Identifying the unpublished comparison snapshot

These checksums identify the read-only local source used for comparison, not an
upstream committed contract or an endorsement of its threshold policy.

- `backend/app/schemas/model_b.py`: `4617233d984fb5f2f631ce56891b39fd8b1c48d7c0beebaa9cfdcd996275aff8`
- `backend/app/ai/model_b_anomaly.py`: `b08e7e8f02673f24518b3572b0547a65486e43476f011abb0c025977df5d072e`
- `backend/app/storage/model_b_store.py`: `9ddf16b3498eba2c6a1b3f5cc61a15c6f173180e1df9798ae90ccd28f36fca45`
- `backend/pyproject.toml`: `fc0030ae05cfe52b0fe15e2e65323e84e680495fe82cade02842957ac918b806`

## Owner review required

1. Approve/revise the v2 contract and the separate trusted scorer composition
   boundary; no backward-compatible auto-migration is claimed.
2. Choose whether decisions stay unassessed, or approve one named threshold policy
   with exact artifact, derivation manifest and authority reference. The software
   has not selected one.
3. Supply a verified original Model B artifact, approved metadata conversion and
   separately authorized loader validation. No historical artifact integrity or
   historical training metrics were established here.
4. Authorize any later Hybrid adapter contract work independently. Until then this
   branch is ready for **contract review only**, not final cross-model integration.
