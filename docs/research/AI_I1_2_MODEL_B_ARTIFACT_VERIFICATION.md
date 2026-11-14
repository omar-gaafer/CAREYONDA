# AI-I1.2 — Trusted Model B artifact compatibility verification

Status: verified local research inference; **canonical decision approval pending**.
All 21 pre-existing reconciliation files were preserved byte-for-byte. This task
adds four files only. No training, artifact writes, staging, commits or pushes.
This report supersedes AI-I1's earlier artifact-unavailable/loader-pending status
for this explicitly identified local enhanced artifact, not Ahmed's original
published all-baseline refit.

## Trust and integrity

The user explicitly authorized deserialization only of this trusted local file:
`CAREYONDA-model-b-integration/artifacts/model_b/seed42-q95-final/model_b_pipeline.joblib`.
Artifact SHA-256:
`c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e`.
Manifest SHA-256 (pinned by existing local training documentation):
`2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132`.
Original metadata SHA-256:
`6271326b7335ec8f7d6d6934e39a0dba4cf02edaf5032149c8bcd7ba1680656d`.

All five manifest-covered file hashes passed. Original files are regular files,
not symlinks; the directory is local and ignored by Git. Permission mode is 0664:
this is not a claim that the filesystem is immutable. Independently supplied pins
and deserialization from the same verified in-memory bytes protect the check/load
boundary. Hashes establish consistency; trusted origin comes from the user's
explicit authorization and previously inspected local training/source records.
No ZIP artifact, discovered alternative, or client-supplied artifact was loaded.

## Compatibility layer

`app.storage.model_b_v1.load_trusted_model_b_v1` requires explicit trust plus both
artifact and manifest pins. Before joblib runs it verifies the exact five-file
manifest, reads each file once with size/symlink checks, validates v1 metadata,
model ID/version, complete feature schema and runtime, and derives v2 metadata
in memory through the canonical `verify_model_b_artifact` mechanism.
After trusted loading it checks Pipeline/imputer/IsolationForest types, fitted
16-column dimensions, median statistics, keep-empty policy, estimator parameters
and fitted tree count. No estimator, original metadata or artifact is migrated,
repacked or overwritten.

Expected model: `model-b-synthetic-isolation-forest` version `1.0.0`.
The original 200-tree, seed-42 forest has effective max_samples=180 and retains
its original score orientation. The canonical service imputes missing predictors
using the verified fitted medians and calls the **same original forest** once;
its output is negated once. A separate verification method exercises the original
fitted pipeline, including its original imputer, for comparison.

The converted metadata digest is
`491d19a612d5aad4a9cbffda81e2f9e5e8250be69dc8ba13f3b7ccfc48b4a3a1`.
This identifies a documented in-memory derivative, not a newly trained model or
an independently issued trust receipt. The original metadata/manifest digests
remain separately available on the loaded bundle. Exact 16-feature order, units,
training-manifest identity and imputation medians are retained.

## Verified experimental configuration versus canonical approval

The verified v1 artifact records threshold `0.5403282173064036`, training-baseline
quantile 0.95, NumPy `method=higher`, strict `score > threshold`. Equality is not
flagged under this recorded experiment. `experimental_policy` carries this exact
configuration with **approval_reference=None**. It is never installed globally.
Even when explicitly passed as context, its missing approval leaves the canonical
result `unassessed` and `flagged=null`. Recorded experimental decisions are compared
separately for reproducibility; they are not approved canonical decisions.

## Actual trusted smoke results

Executed in the already isolated Model B environment: Python 3.12.10, NumPy 2.4.6,
SciPy 1.17.1, scikit-learn 1.9.1, joblib 1.6.0. Versions match artifact metadata
exactly; `pip check` passed. No packages were installed.

- All **780** recorded holdout scores reproduced; maximum absolute difference **0.0**.
- All **780** recorded strict-q95 experimental flags reproduced.
- All **780** canonical results remained scored but **unassessed**, with null flags.
- All rows also matched the original fitted imputer+forest pipeline output.
- **4** partially imputed samples reproduced their saved imputed-feature lists.
- Comparison tolerance: absolute `1e-12`, relative `1e-12`; observed equality was exact.
- Dataset manifest and all six source payload hashes matched training/evaluation
  references. Feature order, units, values and window/feature lineage reconstructed
  exactly from original observations using the unchanged M1.2 extractor.
- Holdout sample/episode IDs were checked against recorded training IDs.

The runner records an actual new local read acquisition time only after reading and
verifying source data; assessment is recorded separately afterwards. The in-memory receipt is matched by the service. Exact local receipt timestamps
are intentionally excluded from this shareable checkpoint.
No original ingestion, mission-event or astronaut acquisition timestamp was created
or changed. Historical source availability remains unknown. ResearchEvidence point
supports describe the existing timestamped synthetic observations, not independently
established physiological exposure intervals. Source/simulation metadata and original
observations remain intact. No NASA data is used or paired with these samples.
No local receipt or sample-level evaluation output was written into Git.

## Reproduction command (trusted local use only)

From the reconciliation worktree root, set `MODEL_B_PYTHON` to the separately
provisioned compatible interpreter, `MODEL_B_ARTIFACT` to the trusted original
artifact directory, and `MODEL_B_DATASET` to the verified seed-42 dataset directory:

```sh
PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 \
"$MODEL_B_PYTHON" \
  -m app.storage.model_b_smoke \
  --artifact "$MODEL_B_ARTIFACT" \
  --dataset "$MODEL_B_DATASET" \
  --expected-artifact-sha256 c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e \
  --expected-manifest-sha256 2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132 \
  --trusted-local-artifact
```

The CLI requires explicit paths and pins, prints aggregate verification only, and
has no fitting or writing path. It is not an API or general untrusted-artifact tool.
It does not manufacture a receipt inside the scoring service.

## Tests and quality gates

- Dedicated Model B tests: **89 passed, 7 skipped**, including 15 new compatibility
  cases with deserialization replaced by a fake. Hash/manifest/trust/runtime/schema/
  unit/model/quantile/symlink failures are rejected before deserialization; synthetic
  fitted-state type/shape/parameter/median mismatches are also rejected.
- Existing canonical tests retain threshold equality coverage for all named policies,
  partial imputation, all-missing abstention, availability/lineage, and unassessed defaults.
- Full relevant backend: **507 passed, 9 skipped, 1 deselected** with an external
  no-training guard. The unchanged Model A fitting test is intentionally deselected.
  Six Model B fitting tests remain opt-in; the historical original baseline artifact
  test and two separate NASA/Model A opt-in tests remain skipped. The original
  published baseline artifact remains distinct from the verified local enhanced one.
- Strict mypy: passed, 86 files, including loader, smoke runner and new tests.
- Ruff lint and format checks: passed. Dependency check and whitespace check: passed.
- No existing tests, research algorithms, APIs, frontend, M2/M4.2, Model A/C or Hybrid
  modules were changed. Fake bundle bytes are tests only, never a runtime fallback.

## Files added and preservation

1. `backend/app/storage/model_b_v1.py`
2. `backend/app/storage/model_b_smoke.py`
3. `backend/tests/unit/test_model_b_v1_compatibility.py`
4. `docs/research/AI_I1_2_MODEL_B_ARTIFACT_VERIFICATION.md`

All 21 prior uncommitted files remain byte-identical. Other existing worktrees retain
source hashes, status, branch and HEAD. Original Model B bundle files remain unchanged.
No generated model, dataset, receipt or per-sample evaluation file is added to Git.

Safe for a separately authorized research checkpoint, with approval explicitly
pending. Remaining requirements: Ahmed's canonical contract/policy approval, trusted
artifact provisioning for teammates, and separately authorized Hybrid boundary work.
The historical single-seed synthetic evaluation does not establish clinical validity,
real-person performance, independent-seed generalization or operational suitability.


## AI-I1.3 checkpoint preparation

The original 25-file reconciliation/verification implementation is retained.
Machine-specific usernames/paths in shareable commands were replaced with generic
examples or explicit environment variables; exact local acquisition timestamps
were removed. No binary artifact, dataset, per-sample evaluation output or local
receipt is included. Historical aggregate research tables remain documentation,
not a newly generated evaluation dataset or an endorsement of clinical validity.
Canonical policy approval remains pending; there is no global q95 activation.


### Exact AI-I1.3 checkpoint inventory

All 25 reviewed source, test, configuration and documentation files:

- `backend/app/ai/anomaly.py`
- `backend/app/ai/baseline.py`
- `backend/app/ai/model_b_anomaly.py`
- `backend/app/schemas/model_b.py`
- `backend/app/storage/model_b_smoke.py`
- `backend/app/storage/model_b_store.py`
- `backend/app/storage/model_b_v1.py`
- `backend/pyproject.toml`
- `backend/requirements-model-b-resolved.txt`
- `backend/tests/unit/test_benign_exercise_control.py`
- `backend/tests/unit/test_model_b_challenger_experiments.py`
- `backend/tests/unit/test_model_b_inference_contract.py`
- `backend/tests/unit/test_model_b_reconciliation.py`
- `backend/tests/unit/test_model_b_v1_compatibility.py`
- `docs/architecture/MODEL_B_AUDIT.md`
- `docs/architecture/MODEL_B_BENIGN_EXERCISE_CONTROL.md`
- `docs/architecture/MODEL_B_VALIDATION_PROTOCOL.md`
- `docs/research/AI_I1_2_MODEL_B_ARTIFACT_VERIFICATION.md`
- `docs/research/AI_I1_MODEL_B_RECONCILIATION.md`
- `docs/research/MODEL_B_PART3_CHALLENGER_EXPERIMENTS.md`
- `docs/research/MODEL_B_PART4_CANDIDATE_EVALUATION_AND_SELECTION.md`
- `docs/research/MODEL_B_PART5_FINAL_DELIVERY_REPORT.md`
- `simulator/research/__init__.py`
- `simulator/research/benign_exercise_control.py`
- `simulator/research/model_b_challenger_experiments.py`
