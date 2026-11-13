# Model A — NASA RR-1 environmental anomaly detector (Isolation Forest)

Status: implemented and trained locally on branch `feature/omar-model-a-training`. Model version 1.1.0 supersedes 1.0.0. The fitted estimator is unchanged; 1.1.0 enforces `*_missing`/value consistency, stops treating missingness indicators as training constants, and keeps test out of candidate-threshold comparisons. Research decision support only; outputs are not diagnoses, hazard determinations, treatment rules or spacecraft commands, and require human review.

This document is safe to publish: it describes method, contracts and limitations. **Evaluation numbers, high-score sample IDs/timestamps and the trained artifact are derived from NASA measurement data whose redistribution is still blocked** (see [the dataset inventory](../research/COMPLETE_DATASET_INVENTORY.md)). They live only in the ignored local artifact directory and must not be committed or shared until that gate is resolved.

## Code layout

| Responsibility | Location |
| --- | --- |
| Persisted metadata contract (Pydantic v2, versioned `1.0.0`) | `backend/app/schemas/nasa_environment_model.py` |
| Inference: column/row validation, train-fitted preprocessing, scoring, threshold decision, provenance (no I/O) | `backend/app/ai/nasa_environment_anomaly.py` |
| Artifact persistence and verified loading (infrastructure adapter) | `backend/app/storage/nasa_environment_model_store.py` |
| Training/evaluation entry point | `backend/app/training/nasa_environment_model_a.py` |
| Tests (synthetic fixtures only) | `backend/tests/unit/test_nasa_environment_anomaly.py`, `backend/tests/integration/test_nasa_environment_model_a.py`, `backend/tests/model_a_fixtures.py` |

The shared `app/ai/anomaly.py` placeholder is intentionally untouched so Model B can proceed independently. No API endpoint is added.

## Inputs

The three chronological processed splits (`train.csv`, `validation.csv`, `test.csv`) plus `manifest.json` and `feature_schema.json` from the D2/D3 NASA export, e.g. `datasets/processed/nasa_rr1_eda_d2d3_validated/` or a fresh local export. Before reading any row the trainer:

- verifies the SHA-256 of **every** file listed in the manifest;
- requires `feature_schema.json` to equal `environmental_schema()` exactly (schema `1.0.0`);
- requires each CSV header to be exactly `sample_id, event_time_utc` followed by the 16 features in schema order;
- checks split row counts against the manifest, strictly increasing timezone-aware timestamps within each split, and non-overlapping chronological splits.

Only the 16 schema features are predictors. `sample_id` and `event_time_utc` are kept separately for traceability. Splits are never mixed or reshuffled. Radiation, synthetic data and any evidence/provenance files are not model inputs. Units are unchanged (CO2 ppm, temperature degC, humidity %, gap s).

## Preprocessing (fitted on `train` only)

- Blank CSV cells are missing values (NaN), never zero. Explicit `NaN`/`inf` values are rejected as invalid; booleans and non-numeric strings are rejected.
- Definitional checks only: `*_missing` must be 0/1; `*_count_30m` must be a non-negative integer; `gap_seconds` must be non-negative. No physiological or environmental range is assumed.
- `*_delta` and `gap_seconds` are structurally blank when there is no earlier reading in the window/split. They are filled with the **training-split median** and listed per row in `imputed_features`.
- `*_missing` is the schema's missing-data indicator. The feature builder sets it to 1 exactly when the timestamp has no valid `*_value`. Inference enforces that definition: an indicator that contradicts its value's presence (1 with a value, or 0 with a blank value) is rejected as invalid input. A consistent indicator of 1 is valid missing data, not an error.
- If a `*_value` or `*_mean_30m` feature is missing, the row **abstains** (no score) with reason `missing_required:<feature>`. A row with `*_missing = 1` therefore abstains through its blank value. The validated training split has no missing main readings, so the model has never learned how a dropout should score. Imputing it would present absent evidence as typical. scikit-learn 1.9 trees can route NaN, but with no NaN seen in training they would send it down the majority branch, which also amounts to "typical". Dropouts are surfaced as abstentions for human review, not as anomaly scores.
- Non-indicator features that were constant in training cannot be represented by the fitted trees. A different value at inference abstains with reason `outside_training_support:<feature>`. In the validated export no non-indicator feature is constant, so this guard does not fire there.
- Invalid input (wrong columns/order, non-numeric, non-finite, a blank non-nullable feature, an out-of-definition flag/count/gap, a contradictory indicator, a naive timestamp) rejects the whole batch with `ModelAInputError`; messages name the row and column but never the value.
- No scaling (tree model).

## Estimator and score

`sklearn.ensemble.IsolationForest` with recorded settings: `n_estimators=200`, `max_samples=256`, `max_features=1.0`, `bootstrap=False`, `contamination="auto"` (unused; `predict()` is not used), `n_jobs=1`, `random_state=42`.

`anomaly_score = -score_samples(x)` is the path-length based Isolation Forest score in (0, 1]; higher means easier to isolate relative to the training sample. It is **uncalibrated** and is not a probability, confidence, severity or clinical/hazard quantity. The scores saturate: split points lie within the training range, so extreme out-of-range values are not ranked above values just beyond the range.

## Threshold (unsupervised heuristic)

`threshold = quantile(training scores, 0.99)` (`training_score_quantile`). It flags about 1 % of training rows by construction and is a review-priority convention, not a hazard threshold. `is_flagged = anomaly_score >= threshold` (inclusive); with no threshold configured, `is_flagged` is `null`.

Selection protocol: candidate thresholds at training quantiles 0.95/0.975/0.99/0.995/0.999 are compared on **train and validation only**. Test is evaluated once, at the fixed threshold. Without anomaly labels there is no defensible criterion for choosing among the candidates, so the pre-declared 0.99 quantile is retained rather than tuned to produce validation flags. Score ties can make neighbouring quantiles identical. The local report shows the tie structure and the trade-offs.

## Evaluation (no labels)

No anomaly ground truth exists, so accuracy, precision, recall, F1 and ROC AUC are neither computed nor meaningful. For each split, `evaluation.json` and `EVALUATION_REPORT.md` report:

- row/scored/abstained/imputed counts;
- score mean, standard deviation and quantiles;
- flagged count/fraction at the selected threshold, and (train/validation only) the candidate-threshold table;
- the highest-scoring rows with `sample_id` and `event_time_utc` for audit;
- the number of distinct scores and the longest run of identical consecutive feature vectors. This is a descriptive diagnostic for possible stale/repeated feeds; no rows are removed.

Seed stability refits with other `random_state` values on the same training rows. It reports the Spearman rank correlation of validation/test scores and the Jaccard overlap of flagged sets. Training-split scores are in-sample.

## Reproduce locally (Windows PowerShell)

From the repository root, with Python 3.11+ x64:

```powershell
py -3.12 -m venv backend\.venv
$careyondaPython = Join-Path (Get-Location) 'backend\.venv\Scripts\python.exe'
& $careyondaPython -m pip install --only-binary=:all: -r .\backend\requirements-model-a.txt
& $careyondaPython -m pip check
$env:PYTHONPATH = Join-Path (Get-Location) 'backend'
& $careyondaPython -m app.training.nasa_environment_model_a `
    --data-dir <processed NASA split directory> `
    --output artifacts\model_a\nasa_rr1_iforest_v1.1.0_rs42
```

The output directory must not exist. Optional flags: `--random-state`, `--n-estimators`, `--max-samples`, `--threshold-quantile`. With identical inputs and pinned dependencies, repeated runs on the same machine produced byte-identical `model.joblib` and identical `evaluation.json`. Cross-platform byte identity has not been checked.

## Artifact location and loading

Artifacts are written to `artifacts/model_a/<run>/` (`model.joblib`, `metadata.json`, `evaluation.json`, `EVALUATION_REPORT.md`). `/artifacts/` and `*.joblib` are git-ignored; do not force-add them. Deliver them only through the team's authorized channel once NASA data-derivative permission is confirmed.

```python
from pathlib import Path
from app.storage.nasa_environment_model_store import load_model_a

detector = load_model_a(Path("artifacts/model_a/nasa_rr1_iforest_v1.1.0_rs42"))
results = detector.score_records(records)  # dicts: sample_id, event_time_utc, 16 features
```

`load_model_a` validates `metadata.json` and requires the runtime scikit-learn version to equal the recorded one. It also verifies the artifact SHA-256 **before** unpickling. joblib files are pickles: load only trusted, locally produced artifacts. Each `AnomalyResult` carries `status` (`scored`/`abstained`), `anomaly_score`, `threshold`, `is_flagged`, `imputed_features`, `abstention_reasons` and provenance: model id/version, artifact hash, feature schema version, dataset manifest hash and threshold method.

`metadata.json` records the dataset name/version, manifest and per-split SHA-256, split sizes and time ranges, the schema version and full feature contract, fitted preprocessing parameters, estimator class and settings, runtime versions, threshold method/value, training rows used/excluded, the score definition, intended use and limitations.

## Dependencies

`backend/pyproject.toml` now declares `numpy>=2.0,<2.5`, `scikit-learn>=1.9,<1.10` and `joblib>=1.4,<2`. `backend/requirements-model-a.txt` pins the tested resolution on top of the unchanged Windows snapshot. numpy 2.5 and scipy 1.18 are excluded because they require Python ≥ 3.12, while the project declares 3.11+ and type-checks against 3.11. Tested on Windows 11 x64 with CPython 3.12.10; the handoff's CPython 3.14 was not available, and 3.11 runtime was not tested.

## Limitations

- No labels: the evaluation is descriptive only. A high score marks a statistically unusual window relative to training, not a confirmed fault or hazard.
- Training data is not certified anomaly-free; anomalous training periods are partly learned as normal and shift the quantile threshold. Review the local report's data-quality diagnostics before relying on the threshold.
- Validation/test follow training chronologically. Flag-rate differences may reflect drift or mission-phase changes. A threshold taken from training quantiles may flag very few or very many later rows.
- The model cannot represent missing-measurement states (constant in training) and abstains on them.
- Single mission (RR-1), ISS experiment environment only; not paired with human physiology; not comparable with synthetic CO2 partial pressure (Pa); radiation excluded.
- Software tests use synthetic fixtures and establish software behavior only, not medical or operational suitability.
