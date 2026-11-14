# Model A Environmental Temporal Research

This is an offline, research-only extension of Model A v1.1.0. It leaves the
production model artifact, preprocessing, inference behavior, M2/M4.2, API routes,
and frontend unchanged. It consumes the validated NASA RR-1 chronological splits and
the trusted local v1.1.0 artifact. Its report and event rows contain
measurement-derived outputs and must remain local until redistribution is cleared.

## Research-only temporal interface v2 (P0 remediation)

`temporal_events.jsonl` emits one record per source event with these fields:

| Field | Meaning |
|---|---|
| `contract_version` | `careyonda.environmental_anomaly_research.v2` |
| `run_mode` | Explicit retrospective research mode |
| `scope` | NASA RR-1 / ISS environmental source; no astronaut or synthetic pairing |
| `model` | Model ID/version, artifact SHA-256, dataset provenance and feature schema version |
| `event` | Original UTC event timestamp, split, evidence reference availability/count, data quality, missing/imputed features and abstention reasons |
| `model_result.score` | Existing uncalibrated Isolation Forest ranking score |
| `model_result.threshold` | Existing training q99 threshold and `>=` comparison |
| `model_result.status` | `flagged`, `not_flagged`, `unassessed`, or `abstained` |
| `model_result.temporal_persistence_2_of_3` | Research-only causal persistence status based on current and prior rows |
| `explanation_limitations` | No probability, accuracy, causal attribution or hazard interpretation |

The output is not a M2/M4.2 schema, a backend API contract, or a request to integrate
this record into production. Evidence reference counts show available lineage in the
local sidecar; they do not authenticate completeness or source acquisition time.
The machine-readable field contract is
[`MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V2.json`](MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V2.json).

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
  causal (past/current only) and a descriptive research signal. All retained rows
  must also fit a total 30-minute lookback, including the boundary.
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

## P0 remediation and interpretation changes

- The core Model A v1.1.0 estimator, preprocessing, artifact and threshold values
  are unchanged. Original threshold comparison remains inclusive `>=`.
- A missing original threshold leaves the score available but the decision
  `unassessed`; it never implies `not_flagged`. Threshold, method and comparison
  are null. Original-threshold counts/fractions and seed-comparison counts are
  null with explicit unassessed status. Separately declared train-quantile
  sensitivity experiments remain independent of the absent original threshold.
- Event contract **v2** replaces absolute `artifact_path` with logical
  `artifact_file` and adds `unassessed`. v1 remains as a historical contract;
  consumers must explicitly adopt v2. Reports identify research method 2.0.0.
  Report manifest and console output references are filenames, not local paths.
- Split files must be nonempty, strictly ordered internally and strictly ordered
  across train/validation/test boundaries. Evidence JSONL must match the hash in
  the already verified dataset manifest before the detector is loaded.
- Persistence now means at least two flags in the current/prior two source rows
  **and within a total 30-minute event-time lookback**, not merely adjacent gaps.
  No history crosses a split boundary. This changes some descriptive persistence
  outcomes without changing any estimator scores or statistical thresholds.
- Recovery is censored at the first unknown reading or gap over 30 minutes;
  later complete runs cannot establish recovery across that missing follow-up.
  Three consecutive scored, non-flagged rows still confirm recovery where
  follow-up is continuous. These are unvalidated research conventions.
- SciPy 1.17.1 is declared directly in the `model-a-research` optional extra,
  matching the existing resolved requirements. No package/version upgrade is
  required. SciPy/sklearn import typing exceptions are narrowly scoped to their
  missing stubs; numerical return values are checked/normalized locally.
- Default strict mypy now includes `scripts/analyze_model_a_environmental.py`.
  Synthetic report-path tests stub loading and alternate-seed fitting: they do
  not load NASA data, deserialize a fitted artifact or train a model.

Verification commands (from backend):

```sh
python -m pytest
python -m mypy --strict app tests ../simulator scripts/analyze_model_a_environmental.py
python -m ruff check app tests ../simulator scripts
python -m ruff format --check app tests ../simulator scripts
python -m pip check
git diff --check
```

The v2 research event is still not an EnvironmentalAnomalyContext,
TemporalSummary or HybridAssessment. Counts/hashes do not establish acquisition
availability or scientific validity; no NASA/human pairing is authorized.

Remediation verification (Python 3.12.10, NumPy 2.4.6, scikit-learn 1.9.1,
SciPy 1.17.1, joblib 1.6.0): 11 focused synthetic research tests passed;
full backend 430 passed, 2 expected local-data skips. Ruff lint/format and strict
mypy including the script passed (78 files); all ten previously reproduced
script typing errors are resolved. Dependency consistency and Git whitespace
checks passed. No packages were installed. Real NASA analysis/seed experiments
were not run, and the original artifact was verified by hashing without loading.

## AI-A3 follow-up

The audited baseline `35cfd99` had already advanced to `9c17223` before AI-A3.
That existing P0 commit contains the threshold, strict typing, chronology,
persistence, recovery-censoring, evidence-hash and path-disclosure fixes described
above. AI-A3 preserves them and adds the following narrowly scoped verification
and provenance behavior:

- Every new event retains the original `feature_observation_ids` mapping when
  available, rather than publishing reference counts alone. An absent record
  yields an empty mapping, not fabricated observation IDs. Duplicate sample IDs,
  malformed mappings and non-string/empty observation IDs are rejected before
  detector loading. The sidecar's manifest hash is still verified first.
- New events explicitly state `historical_source_availability="unknown"` and
  `evidence_availability_scope="lineage_reference_presence_only"`. Reference
  presence is not proof that NASA data was available during its mission; no
  ingestion time, acquisition receipt or replay authorization is manufactured.
- These three event properties are optional additive fields in the v2 JSON
  schema so previously written v2 records remain valid. Current writers always
  emit them. This does not make the event an AI-H1/H2 or Model A API sidecar.
- Synthetic regressions now cover exact threshold equality (`>=` remains
  inclusive), both threshold states with missing measurements, original UTC
  event timestamps, resolvable reference IDs, invalid/ambiguous lineage, the
  inclusive 1800-second adjacent-gap boundary, and censoring beyond that bound.
  Existing tests retain total-lookback, cross-split ordering, absent-threshold
  serialization and report path-disclosure coverage.
- "Stale" in these offline temporal summaries means history outside the declared
  30-minute lookback or follow-up beyond the gap limit. No wall-clock freshness
  or contemporary-exposure claim is made for archived NASA records; there is no
  invented age cutoff relative to today's date.

No algorithm, existing threshold/policy value, dependency pin, trained artifact,
API, frontend or hybrid engine is changed by AI-A3. The analysis still requires
trusted local inputs. Regression fixtures are artificial and stub artifact
loading and alternate-estimator fitting.

AI-A3 verification: 21 focused research regressions passed; the full backend
suite passed 440 tests with 2 expected local-data opt-in skips. Ruff lint and
formatting passed; direct strict mypy including the script passed on 78 files.
`pip check` reported no broken requirements and Git whitespace checks passed.
SciPy remains 1.17.1 under the existing research extra/pins; no dependency was
installed or upgraded. All four trusted artifact-directory files retained their
pre-test SHA-256 hashes. Only synthetic tests were executed; no NASA analysis,
model retraining, trusted artifact loading, API or frontend changes occurred.
