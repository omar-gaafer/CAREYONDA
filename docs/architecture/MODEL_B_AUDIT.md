# Model B — Evaluation Integrity and Implementation Audit

Audit date: 2026-11-14
Scope: read-only audit of synthetic Model B and its available data. No source data, model, or experiment output was modified. No packages were installed, no tests or training were run, and no model artifact was loaded. Descriptive feature statistics below were calculated in memory from the clean seed-42 feature snapshot in Git and checked against the available clean duplicate.

## Executive findings

- Model B is an Isolation Forest pipeline with median imputation, baseline-only fitting, episode-grouped four-fold evaluation, and a final deployment fit on all synthetic baseline episodes.
- The available seed-42 dataset contains 960 samples from 32 episodes: 8 episodes per scenario and 30 samples per episode. Its two other local copies have the same feature and label content, so they do not provide independent validation episodes.
- Grouping is episode-level for the configured 8-episode-per-scenario dataset. There is no separate validation set or untouched test set; the four evaluation folds consume all 960 samples. The user-identified earlier 780-sample result is considered inspected and cannot serve as a fresh test set. It was not reproduced in this audit.
- Strong generator signatures are directly encoded in features. In the clean seed-42 data, elevated-CO2 episodes have much higher simulated CO2; sleep-deprivation episodes have much lower simulated sleep duration and higher ordinal fatigue; recent-exercise episodes have higher heart rate and an exercise flag during about half of their samples. These are scenario shortcuts, not validated health-anomaly labels.
- The checked-out `m1_2_seed42/features.csv` currently has an extra blank first line. `csv.DictReader` consequently produces rows without `sample_id`; `load_dataset()` will fail when it indexes that field. Its SHA-256 is `aa8f15d3…f5bbfc`, while the manifest and clean copies expect `879d2f35…d8106`.
- There is no documented or present Model B baseline artifact/report to inspect. The project does not declare or pin NumPy or scikit-learn, and the existing tests do not cover the Model B trainer or detector.
- No performance metric is reported here. The trainer was not run, and the previous 780-sample result was not independently reproduced.

## Inspected resources

- `backend/app/ai/anomaly.py` — detector, scoring, explanations, serialization.
- `backend/app/ai/baseline.py` — dataset loading, grouped folds, training, evaluation, output writing.
- `backend/app/features/temporal_features.py` and `simulator/mission_generator.py` — feature definitions and synthetic sources.
- `datasets/synthetic/m1_2_seed42/` — canonical seed-42 dataset and manifest.
- `datasets/synthetic/windows_handoff_verification/` and the local ignored `datasets/synthetic/mvp_demo_20261114/` — additional available copies.
- `backend/tests/unit/test_training_pipeline.py` and `backend/tests/integration/test_simulation_cli.py` — tests nearest to Model B inputs.
- `backend/pyproject.toml`, dependency snapshots, `.gitignore`, and Model B documentation/status references.

The working tree already contained modifications to `datasets/synthetic/m1_2_seed42/features.csv` and an untracked `backend/sitecustomize.py`; both were preserved. The audit report is the only file created by this task.

## Architecture and execution path

### Detector

`IsolationForestAnomalyModel` wraps a scikit-learn pipeline:

1. `SimpleImputer(strategy="median")`.
2. `IsolationForest(n_estimators=200, max_samples=256, max_features=1.0, bootstrap=False, contamination="auto", n_jobs=1, random_state=42)` by default.

There is no scaling or learned medical calibration. `feature_names` defines the order for mapping inputs. Mapping inputs silently fill absent names with NaN and ignore extra names; sequence/array inputs use their supplied order and are not checked against names or schema. The detector does not validate input feature count/order itself.

### Training and evaluation

`load_dataset()` reads the feature order from `feature_schema.json`, reads feature rows, joins `labels.csv` by `sample_id`, and joins episode IDs from `evidence_mapping.json`. It does not validate header/schema agreement, duplicate or missing join keys, or manifest hashes before use.

`ModelBTrainer.fit()` calls `build_grouped_folds()`. With the current 8 episodes per scenario, each of four folds holds out two episodes from each scenario. A fold trains on the six non-held-out baseline episodes only; its test rows are all samples in the held-out episodes. The fold model and its imputer are newly fitted each time. After cross-validation, a separate deployment model is fitted on all baseline episodes.

The code maps `baseline` to evaluation truth 0 and every other scenario to truth 1. Labels select baseline training episodes and define evaluation truth; they are not placed in the predictor matrix. The report includes fold metrics, per-scenario recall, episode-level score summaries, and sample predictions. `train_model_b()` can optionally write `model_b_isolation_forest.pkl`, `report.json`, and `predictions.csv`; it is a Python function, not a command-line experiment entry point.

### Inference, scores, flags, and explanations

Inference uses the fitted imputer, then calls either `score_samples()` or `predict()` on the Isolation Forest. Scikit-learn `score_samples()` assigns lower values to more anomalous points; `anomaly_score()` negates them, so larger returned scores mean more anomalous. The flag is `predict() == -1`, converted to integer 1; normal predictions become 0.

The score and flag derive from the same fitted estimator and therefore have a structurally consistent orientation. The wrapper does not expose or persist an explicit numeric decision threshold, assert score/flag consistency, or include a threshold in the report. This audit did not execute the estimator, so consistency and boundary behavior were not independently reproduced.

`explain()` ranks input features by absolute z-deviation from means and standard deviations calculated after median imputation on the training matrix. This is a descriptive deviation ranking, not Isolation Forest feature attribution, causal explanation, calibrated confidence, or evidence/provenance-linked reasoning. For a one-dimensional NumPy input, the code attempts to reshape only after calling the imputer; this path is not covered by tests and may fail before reaching the reshape.

### Serialization

`save()` pickles the pipeline and metadata including feature names, training episode IDs, model/version strings, parameters, and explanation statistics. Opening the target in `wb` overwrites an existing artifact. `train_model_b()` similarly overwrites same-named report/prediction files in an existing output directory. `load()` unpickles without checking type/version/schema or artifact integrity; pickle must only be loaded from a trusted source. No compatibility/reproducibility contract for scikit-learn versions is enforced.

## Data and feature inventory

The clean seed-42 snapshot has 5,760 observations, 960 sample rows, and 16 numeric predictor columns plus `sample_id` metadata. The feature order comes from `feature_schema.json`. The source observations contain 5,612 `valid` and 148 `missing` records. Every one of 32 episodes has 30 samples and exactly one scenario; scenario labels are balanced at 240 samples and 8 episodes each.

The two other available copies (`windows_handoff_verification` and `mvp_demo_20261114`) use the same seed/configuration and have matching SHA-256 values for `features.csv` (`879d2f35…d8106`) and `labels.csv` (`8038dd56…b37945`). They reproduce the same predictor/label rows; they are not independent data. The clean committed seed-42 file has the same feature hash recorded by its manifest.

Every feature is encoded as a number in the CSV. Null counts and descriptive distributions below are from the clean seed-42 predictor rows, not from the modified working copy. Range/mean values are descriptive summaries of this synthetic fixture, not physiological ranges.

| Feature | Meaning/source | Encoding and unit | Nulls / observed distribution |
| --- | --- | --- | --- |
| `heart_rate_latest` | Latest evaluated-valid heart-rate observation in the 5-minute event-time window | Numeric, bpm | 0; min 62.427, max 126.771, mean 81.685 |
| `heart_rate_missing` | No usable heart-rate value anywhere in that window | Binary 0/1 | 0; constant 0 |
| `heart_rate_mean` | Arithmetic mean of usable heart-rate observations in the window | Numeric, bpm | 0; min 63.868, max 126.771, mean 82.178 |
| `cabin_co2_partial_pressure_latest` | Latest evaluated-valid synthetic cabin CO₂ partial pressure | Numeric, Pa | 3; min 45.010, max 174.869, mean 80.073 |
| `cabin_co2_partial_pressure_missing` | No usable CO₂ value in the window | Binary 0/1 | 0; 3 values are 1 |
| `cabin_co2_partial_pressure_mean` | Arithmetic mean of usable CO₂ values in the window | Numeric, Pa | 3; min 45.664, max 173.217, mean 80.037 |
| `sleep_duration_latest` | Latest evaluated-valid synthetic sleep-duration observation | Numeric, hours | 2; min 2.504, max 8.500, mean 6.746 |
| `sleep_duration_missing` | No usable sleep-duration value in the window | Binary 0/1 | 0; 2 values are 1 |
| `sleep_duration_mean` | Arithmetic mean of usable sleep-duration values in the window | Numeric, hours | 2; min 2.625, max 8.490, mean 6.750 |
| `fatigue_self_report_latest` | Latest synthetic fatigue category | Ordinal code: rested=0, tired=1, very_tired=2 | 1; values 0–2, mean 0.687 |
| `fatigue_self_report_missing` | No usable fatigue report in the window | Binary 0/1 | 0; 1 value is 1 |
| `communication_delay_latest` | Latest synthetic communication-delay observation | Numeric, seconds | 1; min 1.800, max 2.200, mean 2.006 |
| `communication_delay_missing` | No usable delay value in the window | Binary 0/1 | 0; 1 value is 1 |
| `communication_delay_mean` | Arithmetic mean of usable delay values in the window | Numeric, seconds | 1; min 1.802, max 2.173, mean 2.002 |
| `exercise_active_latest` | Latest synthetic exercise-state observation | Binary 0/1 encoded numerically | 1; mean 0.125 |
| `exercise_active_missing` | No usable exercise-state value in the window | Binary 0/1 | 0; 1 value is 1 |

There are 14 blank predictor cells out of 15,360 feature cells (about 0.09%). Missing indicators are never null, and the heart-rate missing indicator is constant zero in this snapshot. The source has 148 missing observations, but the rolling window usually supplies an earlier usable value; therefore the feature table substantially masks record-level dropout. A median imputer remains part of the model for other inputs, but missingness behavior is weakly exercised by this dataset.

### Redundancy and scenario shortcuts

`heart_rate_latest` and `heart_rate_mean` have Pearson correlation 0.9904 over the clean seed-42 samples. Other latest/mean pairs reuse overlapping observations and are expected to be redundant. The 5-minute windows advance one minute at a time, so adjacent samples within an episode share most of their evidence and are serially dependent. Random row splitting would leak both episode signatures and overlapping evidence.

Scenario-specific feature means demonstrate direct generator signatures:

| Scenario | Heart rate latest (bpm) | CO₂ partial pressure latest (Pa) | Sleep latest (h) | Fatigue code | Exercise flag |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 73.089 | 49.735 | 7.988 | 0.463 | 0.000 |
| elevated CO₂ | 86.679 | 169.826 | 8.011 | 0.392 | 0.000 |
| recent exercise | 95.893 | 50.300 | 7.983 | 0.389 | 0.500 |
| sleep deprivation | 71.078 | 50.051 | 3.010 | 1.504 | 0.000 |

CO₂ and heart-rate shifts are explicitly programmed for elevated-CO₂ episodes; short sleep and fatigue weighting are programmed for sleep-deprivation episodes; elevated heart rate and the exercise indicator are programmed for exercise episodes. Communication delay is generated similarly across scenarios and is not an obvious intended shortcut. These signals make held-out episodes from the same generator substantially easier than novel health anomalies or generator/domain shift.

Exercise is context, not intrinsically a health anomaly. The trainer labels all 30 samples of every `recent_exercise` episode as positive, although the exercise flag is active for only the first 15 minutes and heart-rate elevation decays. This creates an evaluation-label mismatch for later exercise samples and a false-alert risk if normal activity is interpreted as illness. There is no activity-conditioned baseline or clinical interpretation.

## Evaluation integrity findings

| Check | Finding |
| --- | --- |
| Episode-level split | Correct for the current 8 episodes per scenario: every episode is wholly in one held-out fold; training uses only non-held-out baseline episodes. |
| Group leakage | No within-fold episode overlap in the implemented split. Feature construction scopes evidence by mission/episode. Rows within each episode remain highly dependent; they must stay grouped. |
| General train/validation/test separation | No distinct validation or untouched test partition exists. Four-fold evaluation covers the same 32 episodes across folds; deployment then refits on all baseline episodes. |
| Previous test-set influence | The user identifies an earlier 780-sample evaluation as already inspected. Treat it as development/selection data, not an untouched test. The result was not reproduced here. The repository contains no report tying that count to a specific split. |
| Independent episodes | None are available in the checked-in/ignored copies: the available full-size predictor/label snapshots are duplicate seed-42 data. Independent validation/test episodes would need to be generated and reserved before model selection. |
| Preprocessing leakage | Median imputation is inside each fold model and fitted only on that fold's baseline training matrix; the final imputer is fitted on all baseline training rows. No preprocessing fit on a held-out fold is visible in source. |
| Labels | Scenario labels select baseline training rows and become binary evaluation truth (`baseline`=0, every other scenario=1). They are not predictor columns. This binary mapping is a synthetic assumption, not ground truth for clinical anomalies. |
| Threshold | No validation-based threshold selection. `contamination="auto"` delegates the decision boundary to Isolation Forest; no numeric threshold is written to the report/artifact metadata. |
| Score/flag | Source directions are aligned (`-score_samples` higher means more anomalous; `predict == -1` is flagged). Runtime equality/boundary behavior was not tested or reproduced. |
| Fold implementation | Splitter is hard-coded to two episodes per scenario per fold. It does not validate complete fold coverage, unique sample/episode joins, or robust behavior for other episode counts. |

The code currently computes fold averages and predictions if called, but this audit did not run it. The earlier 780-sample figure cannot be inferred from the checked-in 960-row dataset and no current result file documents its origin. No AUC, precision, recall, F1, or false-alert rate is independently verified here.

## Existing tests and experiment resources

`test_training_pipeline.py` covers simulator determinism, scenario generation, physical/schema constraints, causal feature windows, missing/questionable input handling, feature/evidence export, and non-overwrite behavior for dataset generation. `test_simulation_cli.py` covers simulator CLI output and manifest hashes. These tests do **not** import or exercise `IsolationForestAnomalyModel`, `ModelBTrainer`, `train_model_b()`, score direction, threshold/flag consistency, fold exclusivity, trainer outputs, or model save/load. No Model B experiment script/CLI exists under `scripts/`.

Tests were inspected but not run as part of this read-only audit.

`backend/pyproject.toml` declares Pydantic and development tools only. The current requirements snapshots contain neither NumPy nor scikit-learn, even though Model B imports both. Thus there is no declared reproducible environment for executing or verifying the trainer.

### Documentation drift

`README.md`, `docs/architecture/AI_IMPLEMENTATION_STATUS.md`, `TRAINING_HANDOFF.md`, and `WINDOWS_TRAINING_HANDOFF.md` still describe Model B training as unimplemented. That was true of the earlier `feature/training-ready` baseline, but not of the current `feature/model-b-health-anomaly` source. The docs also do not describe the current trainer, its binary scenario-to-anomaly mapping, or any executed Model B results.

## Baseline artifact availability

The documentation does not identify a concrete Model B baseline artifact path or publish a verified Model B result. The code can write `model_b_isolation_forest.pkl`, but only to a caller-supplied output directory. No `models/`, `artifacts/`, `checkpoints/`, or `runs/` directory or model artifact is present in the inspected repository locations. The available `mvp_demo_20261114` directory contains only dataset/export files, not predictions, a report, or a trained model. No artifact was loaded; there are no contents to verify.

## Critical blockers

1. The working-copy seed-42 CSV is malformed by its leading blank line. The current Model B loader expects `sample_id` in the first CSV header and will fail on this file. Its manifest hash no longer matches. The clean duplicate is usable as input but is the same seed-42 data, not a new evaluation resource.
2. NumPy and scikit-learn are undeclared/unpinned; standard project setup cannot reproducibly provision Model B.
3. There is no independent, untouched validation/test episode set. The 780-sample evaluation is already inspected by instruction, and the 960-sample seed-42 copies are duplicated.
4. Model B has no direct tests and no saved, verified model/report artifact.
5. The built-in `auto` threshold has no validation-set selection or explicit threshold provenance. Scenario-derived labels do not establish clinically meaningful anomaly truth.

## Recommended experiment design

1. Preserve the existing datasets and the previously inspected 780-sample evaluation as development-only material. Do not tune against them and later call them a test set.
2. Provision the declared, pinned offline-compatible NumPy/scikit-learn environment before running a model experiment. Keep experiment outputs in a new, empty directory; do not reuse an output directory that could be overwritten by the current writer.
3. Generate new episodes with a separately recorded seed/configuration. Split by whole episode into baseline training, validation, and an untouched final test set. Keep all 30 temporally overlapping rows from an episode in one partition. Verify IDs, labels, episode membership, feature order, and artifact hashes before fitting.
4. Fit imputation and the detector on training baseline episodes only. Use validation episodes to compare predeclared model variants and choose any threshold. Freeze model, feature schema, binary-label interpretation, and threshold before opening the final test set.
5. Report per-scenario and per-episode behavior, event-level false alerts, missing-data coverage, score distributions, and threshold provenance. Treat “all non-baseline scenarios are anomalies” as an explicitly synthetic evaluation convention. In particular, report exercise separately and do not equate exercise-related deviations with a health hazard.
6. Add direct tests for fold partition integrity, feature order and malformed CSV rejection, train-only imputer fitting, missing/all-missing columns, score direction and flag consistency, deterministic training, and trusted save/load round trips before claiming the pipeline is operational.
7. Store a versioned manifest for the trained artifact and evaluation report: dataset hashes, generator config/seed, episode split IDs, feature order, dependency versions, model parameters, threshold/decision rule, and evaluation code version. Avoid untrusted pickle loading and make output writers refuse existing target files.

This report is an engineering/data-integrity audit only. It does not establish clinical validity, anomaly prevalence, physiological norms, or operational suitability.
