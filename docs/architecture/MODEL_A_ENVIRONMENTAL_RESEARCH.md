# Model A Environmental Temporal Research

This is an offline, research-only extension of Model A v1.1.0. It leaves the
production model artifact, preprocessing, inference behavior, M2/M4.2, API routes,
and frontend unchanged. It consumes the validated NASA RR-1 chronological splits and
the trusted local v1.1.0 artifact. Its report and event rows contain
measurement-derived outputs and must remain local until redistribution is cleared.

## Research-only temporal interface v1

`temporal_events.jsonl` emits one record per source event with these fields:

| Field | Meaning |
|---|---|
| `contract_version` | `careyonda.environmental_anomaly_research.v1` |
| `run_mode` | Explicit retrospective research mode |
| `scope` | NASA RR-1 / ISS environmental source; no astronaut or synthetic pairing |
| `model` | Model ID/version, artifact SHA-256, dataset provenance and feature schema version |
| `event` | Original UTC event timestamp, split, evidence reference availability/count, data quality, missing/imputed features and abstention reasons |
| `model_result.score` | Existing uncalibrated Isolation Forest ranking score |
| `model_result.threshold` | Existing training q99 threshold and `>=` comparison |
| `model_result.status` | `flagged`, `not_flagged`, or `abstained` |
| `model_result.temporal_persistence_2_of_3` | Research-only causal persistence status based on current and prior rows |
| `explanation_limitations` | No probability, accuracy, causal attribution or hazard interpretation |

The output is not a M2/M4.2 schema, a backend API contract, or a request to integrate
this record into production. Evidence reference counts show available lineage in the
local sidecar; they do not authenticate completeness or source acquisition time.
The machine-readable field contract is
[`MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V1.json`](MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V1.json).

## Method

- Preserve the saved v1.1.0 Isolation Forest, feature schema, train-fitted
  preprocessing, and original threshold. The analysis verifies artifact and split
  hashes before use.
- Retain chronological train/validation/test splits. Fit the robust baseline,
  alternative random-seed estimators, and all threshold quantiles on train only.
  Test data is descriptive and never selects a threshold.
- Compare the model with a simple maximum of feature-wise absolute deviation/raw
  MAD values. Medians and raw MADs are fitted only on training. Zero-MAD features
  receive no scaled score; absent measurements remain missing.
- Summarize CO2, temperature, and relative-humidity values and changes by existing
  model status; sampling gaps, missingness/abstention, repeated feature rows, daily
  score distributions, consecutive flagged episodes, and right-censored recovery.
- Temporal persistence is at least 2 flagged scores among the current and previous
  2 rows, with history reset at split boundaries and gaps over 30 minutes. It is
  causal (past/current only) and a descriptive research signal.
- Refit disposable Isolation Forests using seeds 7 and 1234 on train only to compare
  score rankings. The alternate estimators are not persisted.
- No verified anomaly labels exist. Accuracy, precision, recall, F1, and ROC AUC are
  not computed. Differences in scores or flag rates are not confirmed hazards.

## Run on Windows

From the repository root, with the pinned Model A virtual environment and local
inputs available:

```powershell
$env:PYTHONPATH = "backend"
$python = "backend\.venv\Scripts\python.exe"
& $python backend\scripts\analyze_model_a_environmental.py `
  --dataset "Omar-Model-A-Dataset\datasets\processed\nasa_rr1_eda_d2d3_validated" `
  --artifact "artifacts\model_a\nasa_rr1_iforest_v1.1.0_rs42" `
  --output "artifacts\model_a_research\v1.0.0"
```

When running from `backend/`, use `--dataset ..\Omar-Model-A-Dataset\datasets\processed\nasa_rr1_eda_d2d3_validated`, `--artifact ..\artifacts\model_a\nasa_rr1_iforest_v1.1.0_rs42`, and `--output ..\artifacts\model_a_research\v1.0.0`. The output is ignored and must not be committed before distribution approval.

Tests use synthetic values only:

```powershell
cd backend
python -m pytest tests\unit\test_model_a_environmental_research.py -q
```
