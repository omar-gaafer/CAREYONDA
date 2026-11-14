# CAREYONDA Model B Part 5 — Final Research Delivery Report

Date: 2026-11-14  
Status: research-only delivery. No challenger was adopted, no final threshold
was selected, and Final Test remained sealed.

## A. Mission and scope

Model B is a synthetic health-anomaly research detector that fits an
Isolation Forest to baseline samples and scores held-out samples. Parts 1–5
evaluate its research implementation, synthetic data protocol, and candidate
comparisons; they do not establish clinical validity or operational readiness.

This delivery added focused tests for the existing Model B inference/training
contract and consolidated the approved Part 1–4 evidence. It did not rerun
experiments or train candidates.

Excluded: Final Test observations and labels; the previously inspected
780-sample evaluation; new data generation; threshold tuning; production
inference changes; Model A, M2, M4.2, APIs, frontend, and other project tracks.
No dependencies were installed and no Git commit or push was made.

## B. Initial repository inventory and implementation audit

### Git and pre-existing changes

- Branch: `feature/model-b-health-anomaly`.
- Starting HEAD: `28db72b308481cab43c833f67fc56c0d0b22c67b`.
- No staged changes were present at the initial audit.
- A pre-existing tracked modification was present at
  `datasets/synthetic/m1_2_seed42/features.csv` (one extra blank first line).
- Pre-existing untracked paths included `backend/sitecustomize.py`, the
  existing Model B research tests, `docs/architecture/MODEL_B_AUDIT.md`,
  `docs/architecture/MODEL_B_BENIGN_EXERCISE_CONTROL.md`,
  `docs/architecture/MODEL_B_VALIDATION_PROTOCOL.md`,
  `docs/research/MODEL_B_PART3_CHALLENGER_EXPERIMENTS.md`,
  `docs/research/MODEL_B_PART4_CANDIDATE_EVALUATION_AND_SELECTION.md`, and
  `simulator/research/`.
- All pre-existing changes were preserved. The only Part 5 additions are the
  new focused test file and this report.

The Part 1–4 deliverables and existing experiment results were present. The
Part 5 report was absent initially. The current Part 3 implementation, tests,
protocol, results, and prior reports are linked below:

- [Model B audit](../architecture/MODEL_B_AUDIT.md)
- [Validation protocol](../architecture/MODEL_B_VALIDATION_PROTOCOL.md)
- [Benign exercise control design](../architecture/MODEL_B_BENIGN_EXERCISE_CONTROL.md)
- [Part 3 challenger results report](MODEL_B_PART3_CHALLENGER_EXPERIMENTS.md)
- [Part 4 candidate decision](MODEL_B_PART4_CANDIDATE_EVALUATION_AND_SELECTION.md)
- [Research experiment implementation](../../simulator/research/model_b_challenger_experiments.py)
- [Saved experiment results](../../datasets/synthetic/model_b_part3_20261114/challenger_experiments/results.json)

### Existing detector

The original implementation in `backend/app/ai/anomaly.py` uses a median
imputer followed by scikit-learn `IsolationForest`. Default parameters are
200 trees, `max_samples=256`, full feature sampling, `contamination="auto"`,
one job, and random state 42. The imputer and estimator are fitted together
using the rows passed to `fit()`; the trainer in `backend/app/ai/baseline.py`
passes only baseline rows from each training fold.

`score_samples()` follows scikit-learn convention (lower values are more
anomalous). `anomaly_score()` negates those values, so **higher returned
anomaly scores indicate more anomalous samples**. Production `predict()` uses
the estimator's built-in `decision_function`/offset and maps `-1` to an
anomaly flag. There is no public configurable threshold or explicit score to
flag method. The tested built-in relation is
`anomaly_score > -estimator.offset_`; equality is not an anomaly under the
estimator's strict decision boundary. This differs from the exploratory
research threshold rule, which is `score >= threshold`.

Mapping input is read in the model's declared feature order. Array/sequence
input must already use that order. The wrapper does not carry a separately
versioned inference schema. Mapping keys absent from the model feature list
become missing values; additional keys are ignored. Supported missing
representations exercised here are `None`, an empty string, `"nan"`, and
numeric `NaN`. Completely missing feature columns and other missing sentinels
are not certified by these tests.

The baseline trainer creates a new detector for each episode-grouped fold,
collects held-out predictions, then fits a separate deployment detector on
all available baseline episodes. The new synthetic test verifies that
out-of-fold predictions cover the rows once and the returned deployment
model records all baseline training episodes.

### Original baseline artifact and historical metrics

The existing audit and Part 3 report say that no original baseline artifact
was available and historical metrics were not reproduced. The repository
inventory and artifact-output references were checked; no original Model B
pickle/joblib/ONNX/model artifact was located in the inspected project paths.
The trainer can create a caller-directed artifact, but no such original
artifact was available to hash. **Baseline SHA-256 integrity before/after
testing is therefore blocked and unverifiable.** No challenger artifact was
used as a substitute, and no artifact was written or modified.

Historical baseline metrics remain unverified. No claim is made that they
were reproduced.

## C. Validation protocol and data boundaries

The Part 3 input manifests identify 16 ordered numeric features with empty CSV
cells representing missing values; scenario labels are separate from the
predictor matrix. Training and Validation manifests inspected for this report
record:

| Split/role | Seed | Episodes | Samples | Per-scenario episodes / samples |
|---|---:|---:|---:|---:|
| Training | 4201 | 500 | 15,000 | 100 / 3,000 |
| Original Validation | 4202 | 150 | 4,500 | 30 / 900 |
| Calibration subset | 4244 partition seed | 75 | 2,250 | 15 / 450 |
| Evaluation subset | 4244 partition seed | 75 | 2,250 | 15 / 450 |
| Final Test, reserved | 4203 | 150 planned | 4,500 planned | 30 / 900 planned |

Calibration and Evaluation are deterministic, scenario-stratified partitions
of whole Validation episodes. Calibration is used to derive exploratory
thresholds; Evaluation is used for candidate comparison and metrics. The
results JSON records zero Calibration/Evaluation overlap for episode,
sample, observation, and evidence-observation IDs. The experiment code also
fails closed on Training/Validation overlap before fitting; the report records
that these checks completed. The Final Test split was not opened to verify
its files or labels during Part 5.

Synthetic proxy mapping: baseline and benign exercise control are negative;
elevated CO2, recent exercise, and sleep deprivation are positive. Recent
exercise remains a positive proxy and is not counted as benign-control false
positives. These labels encode simulator scenarios and are not clinical
ground truth.

The saved results use Python 3.14.2, NumPy 2.4.6, and scikit-learn 1.9.1;
the test environment used Python 3.14.2. The Part 3 manifests record 16
features and distinct Training/Validation payload hashes. No dataset was
regenerated for Part 5.

## D. Candidate configurations and actual results

Each row reports the existing Part 3 JSON at its exploratory Calibration
baseline-score 95th-percentile threshold. Evaluation has 2,250 samples, with
1,350 positive-proxy samples and 900 negative-proxy samples. Baseline FPR
uses 450 baseline samples. Benign and recent active-exercise alert rates each
use 225 active-exercise samples. Counts are alert or episode numerators over
their eligible sample or episode denominators; they are not scores or
independent observations.

Scenario recall order: elevated CO2 / recent exercise / sleep deprivation.
Episode detection order: baseline / benign control / elevated CO2 / recent
exercise / sleep deprivation. Episode detection is episodes with at least
one flagged sample out of 15 Evaluation episodes per scenario.

| Candidate | Configuration in saved results | Precision | Recall | F1 | PR-AUC (average precision) | Scenario recall | Baseline FPR | Benign active alerts | Recent active alerts | Episode detection (B / BC / CO2 / R / S) |
|---|---|---:|---:|---:|---:|---|---|---|---|---|
| Reference IF 200 | Isolation Forest: 200 trees, 256 samples, all features, seed 42 | 0.851 | 0.780 | 0.814 | 0.894 | 1.000 / 0.576 / 0.764 | 21/450 (0.047) | 114/225 (0.507) | 134/225 (0.596) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 500 trees | 500 trees, 256 samples, all features, seed 42 | 0.868 | 0.745 | 0.802 | 0.903 | 1.000 / 0.447 / 0.789 | 16/450 (0.036) | 96/225 (0.427) | 105/225 (0.467) | 8/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 75% feature sampling | 200 trees, 256 samples, 75% feature sampling, seed 42 | 0.868 | 0.761 | 0.811 | 0.910 | 1.000 / 0.473 / 0.809 | 20/450 (0.044) | 91/225 (0.404) | 118/225 (0.524) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 128 subsamples | 200 trees, 128 samples, all features, seed 42 | 0.858 | 0.741 | 0.795 | 0.883 | 0.996 / 0.458 / 0.771 | 25/450 (0.056) | 100/225 (0.444) | 108/225 (0.480) | 9/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Robust MAD distance | Training-baseline median/MAD distance with saved fallback scale rules | 0.887 | 0.955 | 0.920 | 0.983 | 1.000 / 0.864 / 1.000 | 15/450 (0.033) | 125/225 (0.556) | 225/225 (1.000) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Without heart-rate features | Reference IF; removes `heart_rate_latest`, `heart_rate_missing`, `heart_rate_mean` | 0.945 | 0.506 | 0.659 | 0.888 | 0.544 / 0.044 / 0.929 | 20/450 (0.044) | 14/225 (0.062) | 10/225 (0.044) | 12/15 / 14/15 / 15/15 / 11/15 / 15/15 |
| Without exercise features | Reference IF; removes `exercise_active_latest`, `exercise_active_missing` | 0.894 | 0.669 | 0.765 | 0.897 | 0.947 / 0.273 / 0.787 | 11/450 (0.024) | 68/225 (0.302) | 73/225 (0.324) | 8/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Without both groups | Reference IF; removes heart-rate and exercise feature groups | 0.944 | 0.371 | 0.533 | 0.878 | 0.289 / 0.036 / 0.789 | 14/450 (0.031) | 11/225 (0.049) | 8/225 (0.036) | 10/15 / 12/15 / 15/15 / 11/15 / 15/15 |
| Causal 3-sample score mean | Mean of current and previous two reference scores; reset at each episode | 0.853 | 0.847 | 0.850 | 0.908 | 1.000 / 0.682 / 0.858 | 11/450 (0.024) | 139/225 (0.618) | 158/225 (0.702) | 7/15 / 15/15 / 15/15 / 15/15 / 15/15 |

Precision, recall, F1, PR-AUC, and scenario recall are Evaluation sample-level
metrics. The saved JSON uses average precision as its PR-AUC convention.
PR-AUC confidence intervals are unavailable.

### Available 95% episode-bootstrap intervals

The saved intervals resample whole Evaluation episodes within scenario for
1,000 replicates (seed 4243). Metric intervals condition on the fitted model,
fixed scores, and the fixed exploratory threshold; they do not quantify
refitting or threshold-reselection uncertainty. Scenario interval order is
elevated CO2 / recent exercise / sleep deprivation; episode interval order is
baseline / benign control / elevated CO2 / recent exercise / sleep deprivation.

| Candidate | Precision / recall / F1 | Scenario-recall intervals | Baseline FPR / benign-active / recent-active intervals | Episode-alert-rate intervals |
|---|---|---|---|---|
| Reference IF 200 | 0.822–0.878 / 0.758–0.803 / 0.794–0.833 | 1.000–1.000 / 0.520–0.627 / 0.724–0.804 | 0.024–0.076 / 0.427–0.600 / 0.511–0.680 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 500 trees | 0.839–0.895 / 0.724–0.766 / 0.784–0.819 | 1.000–1.000 / 0.402–0.484 / 0.744–0.833 | 0.013–0.064 / 0.351–0.516 / 0.387–0.542 | 0.267–0.733 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 75% feature sampling | 0.840–0.893 / 0.736–0.787 / 0.791–0.830 | 1.000–1.000 / 0.413–0.529 / 0.762–0.856 | 0.029–0.060 / 0.333–0.480 / 0.431–0.618 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 128 subsamples | 0.826–0.887 / 0.715–0.767 / 0.775–0.815 | 0.987–1.000 / 0.400–0.511 / 0.722–0.820 | 0.022–0.096 / 0.369–0.525 / 0.404–0.560 | 0.333–0.867 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Robust MAD distance | 0.851–0.916 / 0.927–0.982 / 0.894–0.941 | 1.000–1.000 / 0.780–0.947 / 1.000–1.000 | 0.020–0.049 / 0.422–0.702 / 1.000–1.000 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Without heart-rate features | 0.933–0.956 / 0.483–0.530 / 0.638–0.680 | 0.480–0.607 / 0.027–0.064 / 0.904–0.951 | 0.031–0.058 / 0.040–0.089 / 0.022–0.071 | 0.600–1.000 / 0.800–1.000 / 1.000–1.000 / 0.467–0.933 / 1.000–1.000 |
| Without exercise features | 0.869–0.916 / 0.648–0.690 / 0.749–0.782 | 0.911–0.976 / 0.238–0.309 / 0.747–0.822 | 0.011–0.038 / 0.244–0.369 / 0.267–0.378 | 0.267–0.800 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Without both groups | 0.928–0.959 / 0.351–0.393 / 0.511–0.556 | 0.240–0.344 / 0.020–0.053 / 0.758–0.818 | 0.018–0.044 / 0.031–0.067 / 0.018–0.058 | 0.400–0.867 / 0.600–1.000 / 1.000–1.000 / 0.467–0.933 / 1.000–1.000 |
| Causal 3-sample score mean | 0.825–0.878 / 0.820–0.873 / 0.829–0.869 | 1.000–1.000 / 0.624–0.742 / 0.807–0.907 | 0.009–0.042 / 0.533–0.707 / 0.618–0.782 | 0.200–0.733 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |

The Calibration q95 bootstrap threshold distributions (lower / median / upper)
are: reference IF `0.5320 / 0.5405 / 0.5511`; IF 500 `0.5271 / 0.5397 /
0.5518`; IF 75% `0.5322 / 0.5393 / 0.5501`; IF 128 `0.5355 / 0.5491 /
0.5594`; robust MAD `0.9909 / 1.0333 / 1.0583`; without heart rate
`0.5380 / 0.5421 / 0.5535`; without exercise `0.5302 / 0.5487 / 0.5520`;
without both `0.5519 / 0.5587 / 0.5654`; temporal mean `0.5221 / 0.5398 /
0.5496`. These are descriptive quantile-score distributions, not the
protocol's constrained feasible-threshold selection stability analysis.
No feasible-resample fraction or PR-AUC interval is available.

## E. Candidate decision

The Part 4 decision is retained: **reject challenger adoption for now and
retain original Model B as the recommendation; approve no new configuration
or threshold.** This does not certify the original Model B as safe, effective,
or compliant with an alert budget.

The protocol requires numeric `B_max` and `E_max` to be set before selection,
then chooses the feasible threshold maximizing unweighted macro scenario
recall with predeclared tie-breakers. Both limits remain unapproved. The
available q95 operating points are not a full constrained-threshold search,
so no challenger is demonstrated to satisfy the protocol. No final threshold
was selected.

Evaluation has already been used for candidate comparison. It is therefore
exploratory and cannot serve as independent confirmatory evidence for a
candidate chosen from these results. A future confirmatory analysis requires
approved budgets, a frozen candidate/protocol, and a one-time evaluation of
the sealed Final Test. None of those steps occurred here.

## F. Feature ablation and scenario error analysis

- Baseline sample false positives at q95 ranged from 11/450 (0.024) to 25/450
  (0.056). Reference IF produced 21/450 (0.047); robust MAD produced 15/450
  (0.033). Episode-level baseline any-alert rates ranged from 7/15 to 12/15;
  reference IF alerted in 11/15 baseline episodes.
- Benign-control active-exercise alert rates ranged from 11/225 (0.049) to
  139/225 (0.618). Reference IF alerted in 114/225 (0.507); robust MAD
  alerted in 125/225 (0.556). All candidates except the two ablations without
  heart rate or without both feature groups alerted in all 15 benign-control
  episodes.
- Recent-exercise active alert rates are separate positive-scenario
  descriptors: 8/225 (0.036) to 225/225 (1.000). Reference IF was 134/225
  (0.596). Recent-exercise sample recall ranged from 0.036 to 0.864. The
  without-heart-rate and without-both ablations detected 11/15 recent-exercise
  episodes, missing 4 each; the other candidates detected 15/15.
- Removing heart-rate features reduced benign active alerts from 114/225 to
  14/225 and recent active alerts from 134/225 to 10/225. It also reduced
  pooled recall from 0.780 to 0.506, elevated-CO2 recall from 1.000 to 0.544,
  and recent-exercise recall from 0.576 to 0.044.
- Removing exercise features alone reduced pooled recall to 0.669 and
  recent-exercise recall to 0.273. Removing both groups reduced pooled recall
  to 0.371, elevated-CO2 recall to 0.289, and recent-exercise recall to 0.036.
- The Part 3 report records Evaluation active-sample mean
  `heart_rate_latest` of 86.11 for benign controls and 102.66 for recent
  exercise; Training means were 87.46 and 103.51. The hand-set half-response
  for benign control versus full configured exercise response is a potential
  synthetic shortcut, not a basis for real-world discrimination claims.
- The research adapter keeps labels, scenario names, IDs, and metadata outside
  the model input matrix; its saved run records `labels_used_as_features=false`.
  Direct predictor leakage was not identified in the reviewed implementation.
  Synthetic label construction, repeated correlated samples, and the
  Validation candidate comparison remain important sources of optimism.
- Bootstrap intervals are episode-based but condition on the fitted model,
  fixed scores, and exploratory threshold. They do not measure model-refitting,
  candidate-selection, or threshold-reselection uncertainty. Only 15
  Evaluation episodes per scenario are available.

## G. Automated test results

New tests are isolated in
`backend/tests/unit/test_model_b_inference_contract.py`. No production code was
changed.

| Category | Status | Test evidence / limitation |
|---|---|---|
| Anomaly score direction | PASS | `test_anomaly_score_is_higher_for_a_distant_sample` fits the detector and checks a distant synthetic sample scores higher. |
| Score-to-flag consistency | PASS | `test_predict_flags_match_the_detector_score_and_internal_threshold` checks production `predict()` flags against its fitted estimator offset and higher-is-more-anomalous score. |
| Threshold behavior | PASS | `test_documented_exploratory_threshold_is_inclusive` tests below, equal, and above values for the documented research `>=` rule. Production `predict()` has a separate strict built-in offset boundary, also checked above. |
| Missing-value handling | PASS, bounded | `test_supported_missing_values_use_training_medians_without_mutation` checks `None`, empty string, `"nan"`, and numeric `NaN`; all-missing feature columns and other sentinels remain unverified. |
| Episode boundary handling | PASS | The temporal test checks the first sample in a new episode starts with its own score rather than carrying the prior episode's history. |
| Temporal smoothing without future leakage | PASS | `test_causal_smoothing_is_future_invariant_and_resets_between_episodes` changes later scores and verifies earlier episode outputs do not change. |
| Training-only preprocessing | PASS | The test checks imputer medians equal Training-only medians before and after extreme held-out input; the trainer test checks separate OOF folds and all-baseline deployment fit. |
| Reproducibility | PASS | Same synthetic training input and random state yield identical anomaly scores. |
| Feature ordering and inference contract | PASS, bounded | Mapping input follows declared order; wrong array dimensionality raises; the Part 3 Training manifest feature order has 16 predictor names and no label/scenario names. No versioned public inference schema is present. |
| Original baseline artifact integrity | BLOCKED | Test skipped because no original artifact was located. Before/after SHA-256 comparison cannot be performed; no substitute artifact was used. |

Final executed test commands and results:

| Command (from `backend`) | Exit | Result |
|---|---:|---|
| `& .\.venv\Scripts\python.exe -m pytest -q tests\unit\test_model_b_inference_contract.py` | 0 | 11 passed, 1 skipped (baseline artifact unavailable). |
| `& .\.venv\Scripts\python.exe -m pytest -q tests\unit\test_model_b_challenger_experiments.py tests\unit\test_benign_exercise_control.py` | 0 | 18 passed. |
| `& .\.venv\Scripts\python.exe -m pytest -q tests\unit\test_training_pipeline.py tests\integration\test_simulation_cli.py` | 0 | 31 passed. |
| Combined command with all five test files | 0 | 60 passed, 1 skipped. |

The combined command was:

```powershell
Set-Location C:\Users\HP\Desktop\CAREYONDA\backend
$env:PYTHONPATH = 'C:\Users\HP\Desktop\CAREYONDA;C:\Users\HP\Desktop\CAREYONDA\backend'
& .\.venv\Scripts\python.exe -m pytest -q tests\unit\test_model_b_inference_contract.py tests\unit\test_model_b_challenger_experiments.py tests\unit\test_benign_exercise_control.py tests\unit\test_training_pipeline.py tests\integration\test_simulation_cli.py
```

Final Ruff checks (exit 0):

```powershell
Set-Location C:\Users\HP\Desktop\CAREYONDA\backend
& .\.venv\Scripts\python.exe -m ruff check tests\unit\test_model_b_inference_contract.py tests\unit\test_model_b_challenger_experiments.py tests\unit\test_benign_exercise_control.py
& .\.venv\Scripts\python.exe -m ruff format --check tests\unit\test_model_b_inference_contract.py tests\unit\test_model_b_challenger_experiments.py tests\unit\test_benign_exercise_control.py
```

Verification iteration history is retained for transparency:

- The first focused test attempt exited 1 (28 passed, 1 failed, 1 skipped):
  its small fixture triggered the existing `max_samples=256` warning, treated
  as an error by test configuration. The fixture was enlarged; production
  code was not changed.
- The next attempt exited 1 (28 passed, 1 failed, 1 skipped) because the
  test compared a per-sample episode list to unique episode IDs. The assertion
  was corrected to compare unique episode sets.
- The first Ruff lint/format checks exited 1 on import ordering and formatting;
  the new test file was formatted, then both final checks passed.
- The final focused and combined test runs above passed. The one skip remains
  the unavailable original artifact integrity check.

## H. Reproduction instructions and command verification

The existing local environment is Python 3.14.2; no packages were installed.
Environment preparation and version check (executed successfully):

```powershell
Set-Location C:\Users\HP\Desktop\CAREYONDA\backend
$env:PYTHONPATH = 'C:\Users\HP\Desktop\CAREYONDA;C:\Users\HP\Desktop\CAREYONDA\backend'
& .\.venv\Scripts\python.exe --version
```

The validation protocol is a specification document, not an executable
protocol runner. There is no separately verified command to re-run protocol
selection without data/model work: **UNVERIFIED**. The Part 3 data generation
was intentionally not rerun; the current research directory has no standalone
Part 3 three-split generation runner identified during this task.

The approved Part 3 challenger script runs all nine candidates and writes to
the existing `datasets\synthetic\model_b_part3_20261114\challenger_experiments\results.json`
by replacing it. The exact command implied by its entry point is:

```powershell
Set-Location C:\Users\HP\Desktop\CAREYONDA\backend
$env:PYTHONPATH = 'C:\Users\HP\Desktop\CAREYONDA;C:\Users\HP\Desktop\CAREYONDA\backend'
& .\.venv\Scripts\python.exe ..\simulator\research\model_b_challenger_experiments.py
```

This command was **not run**: it would rerun experiments and overwrite the
approved results JSON, both prohibited in Part 5. Its successful reproduction
is therefore **UNVERIFIED**. Part 4 has no independent experiment runner; its
candidate decision is documented from the saved Part 3 JSON. Do not run the
Part 3 command solely to reproduce this report.

Test and lint commands above were actually run with the recorded outcomes.
No command for Final Test access, model training for deployment, or threshold
selection is provided or authorized.

## I. Inference contract

The existing detector contract remains as audited: declared feature order,
numeric anomaly scores with higher values indicating more anomalous samples,
and production flags from the estimator's built-in decision boundary.
**No inference contract changes were made in Part 5.**

## J. Limitations and follow-up

- Synthetic proxy labels are simulator scenario indicators, not clinical
  anomaly truth, and do not support medical or flight-control decisions.
- The original Model B baseline artifact and its historical metrics were not
  available for integrity verification or reproduction.
- Evaluation was already used to compare candidates, so its metrics are
  exploratory and affected by candidate-selection optimism.
- Episode-bootstrap intervals quantify limited episode resampling conditional
  on a fitted model and fixed threshold; they omit refitting and
  threshold-selection uncertainty.
- `B_max` and `E_max` remain unapproved. No threshold or challenger is
  approved, and no production-readiness claim is made.
- The Final Test directory and its observations/labels were not accessed.
  Test-artifact integrity is blocked because the original baseline artifact
  was not found. The validation-protocol execution and experiment-regeneration
  commands remain unverified because they would require prohibited data or
  output changes.

## Git delivery status

No files were staged. The proposed Part 5 staging list, if separately
approved, is exactly:

1. `backend/tests/unit/test_model_b_inference_contract.py`
2. `docs/research/MODEL_B_PART5_FINAL_DELIVERY_REPORT.md`

The pre-existing unstaged change to the historical seed-42 feature CSV and
all pre-existing untracked research files remain outside that proposed list.
No commit-related action has been performed.
