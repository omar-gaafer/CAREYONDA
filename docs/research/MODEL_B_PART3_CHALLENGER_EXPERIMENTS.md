# CAREYONDA Model B Part 3 — Challenger Experiments

Status: exploratory research-only comparison. Validation episodes were split
into separate Calibration and Evaluation subsets. No final candidate or
threshold was selected. `B_max` and `E_max` remain unapproved. Final Test was
not accessed.

## Data, partition, and reproducibility

Training used the generated `training_seed_4201` split only for model fitting
and preprocessing: 500 episodes and 15,000 samples (100 episodes and 3,000
samples per scenario). The original Validation split (`validation_seed_4202`)
contained 150 episodes and 4,500 samples (30 episodes and 900 samples per
scenario).

Validation was deterministically partitioned by scenario and whole episode
using seed 4244 and a 50% Calibration fraction. Calibration contained 75
episodes and 2,250 samples (15 episodes and 450 samples per scenario).
Evaluation contained 75 episodes and 2,250 samples (15 episodes and 450
samples per scenario). All 30 samples of each episode remain together.
Episode, sample, and evidence-observation ID overlap counts between subsets
were all zero. The script fails closed on overlap, including Training against
either Validation subset.

Calibration is used only to derive exploratory baseline-score quantile
thresholds and describe threshold stability. Candidate performance metrics,
temporal-method metrics, episode bootstrap metric intervals, and exercise
feature summaries use Evaluation only. No threshold is selected from
Evaluation. Fitted preprocessing uses only the 3,000 Training baseline rows.

The output JSON records Training and original Validation payload SHA-256
hashes, input and partition seeds, Python/NumPy/scikit-learn versions, and all
candidate parameters. The run used Python 3.14.2, NumPy 2.4.6, and
scikit-learn 1.9.1. The proxy mapping is baseline and benign exercise control
= negative; elevated CO2, recent exercise, and sleep deprivation = positive.
These are synthetic evaluation proxies, not clinical truth.

The reference Isolation Forest uses 200 trees, `max_samples=256`, full feature
sampling, and random state 42, scored as `-score_samples` so higher values
indicate more anomalous. No historical baseline artifact was available, and
no historical metric reproduction is claimed.

## Methods

Candidates were fitted on Training baseline episodes only:

| Candidate | Configuration |
|---|---|
| `if_reference_200` | 200 trees, 256 samples, all features |
| `if_more_trees_500` | 500 trees, 256 samples, all features |
| `if_random_subspace_75pct` | 200 trees, 256 samples, 75% feature sampling |
| `if_smaller_subsamples_128` | 200 trees, 128 samples, all features |
| `robust_mad_distance` | Per-feature median/MAD distance; zero-MAD fallback IQR/1.349, then standard deviation, then 1 |
| `ablation_without_heart_rate` | Reference Isolation Forest without all three heart-rate features |
| `ablation_without_exercise` | Reference Isolation Forest without both exercise features |
| `ablation_without_heart_rate_or_exercise` | Reference Isolation Forest without either feature group |
| `temporal_causal_3sample_mean` | Mean of current and previous two reference scores |

Temporal processing sorts by event timestamp and then sample ID, resets state
at episode boundaries, and uses no future samples. Persistence separately
flags when at least two of the current and preceding two raw reference scores
exceed the Calibration-derived reference 5% baseline quantile.

All thresholds are exploratory. Each candidate's Calibration baseline score
quantiles (99th, 95th, 90th, 80th, and 50th) are applied unchanged to
Evaluation. Episode-bootstrap metric intervals resample Evaluation episodes
within scenario and condition on the fitted model, fixed Evaluation scores,
and fixed Calibration-derived threshold. They are not full-pipeline
uncertainty estimates; threshold-stability intervals resample Calibration
episodes only.

## Evaluation results

The table reports Evaluation results at the exploratory Calibration 95th
percentile threshold. Rate counts are `alerts / eligible samples`; scenario
recall order is elevated CO2 / recent exercise / sleep deprivation. Baseline
FPR uses 450 Evaluation baseline samples. The active exercise denominators
are 225 benign-control and 225 recent-exercise samples with
`exercise_active_latest == 1`. Recent exercise remains a separate positive
scenario and is not included in benign-control FPR.
The results JSON records numerator/denominator counts for precision, recall,
scenario recall, sample alert rates, and episode alert rates. Active-exercise
denominators are based on the exercise flag and may include samples with
missing heart rate; the heart-rate distribution summary counts only finite
heart-rate observations.

| Candidate | Precision | Recall | F1 | PR-AUC | Baseline FPR | Benign active alerts | Recent active alerts | Scenario recall |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Reference IF 200 | 0.851 | 0.780 | 0.814 | 0.894 | 21/450 (0.047) | 114/225 (0.507) | 134/225 (0.596) | 1.000 / 0.576 / 0.764 |
| IF 500 trees | 0.868 | 0.745 | 0.802 | 0.903 | 16/450 (0.036) | 96/225 (0.427) | 105/225 (0.467) | 1.000 / 0.447 / 0.789 |
| IF 75% feature sampling | 0.868 | 0.761 | 0.811 | 0.910 | 20/450 (0.044) | 91/225 (0.404) | 118/225 (0.524) | 1.000 / 0.473 / 0.809 |
| IF 128 subsamples | 0.858 | 0.741 | 0.795 | 0.883 | 25/450 (0.056) | 100/225 (0.444) | 108/225 (0.480) | 0.996 / 0.458 / 0.771 |
| Robust MAD distance | 0.887 | 0.955 | 0.920 | 0.983 | 15/450 (0.033) | 125/225 (0.556) | 225/225 (1.000) | 1.000 / 0.864 / 1.000 |
| Without heart rate | 0.945 | 0.506 | 0.659 | 0.888 | 20/450 (0.044) | 14/225 (0.062) | 10/225 (0.044) | 0.544 / 0.044 / 0.929 |
| Without exercise features | 0.894 | 0.669 | 0.765 | 0.897 | 11/450 (0.024) | 68/225 (0.302) | 73/225 (0.324) | 0.947 / 0.273 / 0.787 |
| Without both groups | 0.944 | 0.371 | 0.533 | 0.878 | 14/450 (0.031) | 11/225 (0.049) | 8/225 (0.036) | 0.289 / 0.036 / 0.789 |
| Causal 3-sample score mean | 0.853 | 0.847 | 0.850 | 0.908 | 11/450 (0.024) | 139/225 (0.618) | 158/225 (0.702) | 1.000 / 0.682 / 0.858 |

Episode-level “any alert” counts are `episodes with any alert / total
Evaluation episodes` in scenario order baseline / benign control / elevated
CO2 / recent exercise / sleep deprivation:

| Candidate | Baseline | Benign control | Elevated CO2 | Recent exercise | Sleep deprivation |
|---|---:|---:|---:|---:|---:|
| Reference IF 200 | 11/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| IF 500 trees | 8/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| IF 75% feature sampling | 11/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| IF 128 subsamples | 9/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| Robust MAD distance | 11/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| Without heart rate | 12/15 | 14/15 | 15/15 | 11/15 | 15/15 |
| Without exercise features | 8/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| Without both groups | 10/15 | 12/15 | 15/15 | 11/15 | 15/15 |
| Causal 3-sample score mean | 7/15 | 15/15 | 15/15 | 15/15 | 15/15 |

At the reference persistence operating rule, Evaluation baseline FPR was 2/450;
benign active-exercise alerts were 105/225. One of 15 baseline episodes had an
alert, while all 15 benign-control episodes had at least one.

## Exploratory threshold trade-offs

For each cell: Evaluation baseline FPR (`alerts/450`) / pooled positive recall
/ benign active alerts (`alerts/225`) / recent active alerts (`alerts/225`).
The percentile threshold is derived only from Calibration baseline scores.

| Candidate | 99th percentile | 95th percentile | 90th percentile | 80th percentile | 50th percentile |
|---|---|---|---|---|---|
| Reference IF 200 | 2/450 / 0.421 / 32/225 / 35/225 | 21/450 / 0.780 / 114/225 / 134/225 | 40/450 / 0.908 / 164/225 / 198/225 | 100/450 / 0.990 / 201/225 / 224/225 | 229/450 / 1.000 / 217/225 / 225/225 |
| Robust MAD distance | 4/450 / 0.792 / 12/225 / 159/225 | 15/450 / 0.955 / 125/225 / 225/225 | 35/450 / 0.978 / 166/225 / 225/225 | 85/450 / 0.990 / 191/225 / 225/225 | 223/450 / 1.000 / 218/225 / 225/225 |
| Without heart rate | 0/450 / 0.121 / 2/225 / 2/225 | 20/450 / 0.506 / 14/225 / 10/225 | 33/450 / 0.585 / 21/225 / 15/225 | 70/450 / 0.716 / 47/225 / 41/225 | 207/450 / 0.825 / 114/225 / 114/225 |

The Calibration quantile's target FPR is not the Evaluation FPR; the latter is
measured independently on Evaluation. None of these operating points is
asserted to meet an approved `B_max` or `E_max`.

## Feature ablations and synthetic cue

On Evaluation active-exercise samples, `heart_rate_latest` means were 86.11
for benign controls (225 samples) and 102.66 for recent exercise (223 samples);
medians were 85.87 and 102.43. Training means were 87.46 and 103.51,
respectively. The separation is consistent with the generator's hand-set
response fraction (0.5 for control versus full configured exercise response).
This is a synthetic shortcut risk, not evidence that real benign exercise can
be distinguished from a health hazard.

Removing heart-rate features reduces benign and recent active-exercise alerts
at the exploratory point, but also reduces recent-exercise recall to 0.044 and
elevated-CO2 recall to 0.544. Removing exercise features alone yields 0.302
benign active alert rate and 0.273 recent-exercise recall. These ablations are
exploratory comparisons, not feature-selection decisions.

## Episode-bootstrap uncertainty

Selected 95% episode-bootstrap intervals at fixed Calibration-derived
exploratory thresholds:

| Candidate / metric | Evaluation estimate | 95% interval |
|---|---:|---:|
| Reference precision | 0.851 | 0.822–0.878 |
| Reference recall | 0.780 | 0.758–0.803 |
| Reference F1 | 0.814 | 0.794–0.833 |
| Reference baseline FPR | 0.047 | 0.024–0.076 |
| Reference benign active alert rate | 0.507 | 0.427–0.600 |
| Reference recent active alert rate | 0.596 | 0.511–0.680 |
| Reference calibration-threshold stability | — | 0.5320–0.5511 |
| Robust MAD recall | 0.955 | 0.927–0.982 |
| Robust MAD benign active alert rate | 0.556 | 0.422–0.702 |
| Without-heart-rate recall | 0.506 | 0.483–0.530 |
| Without-heart-rate benign active alert rate | 0.062 | 0.040–0.089 |

Metric intervals resample Evaluation episodes within scenario and condition on
the fitted model, fixed Evaluation scores, and fixed Calibration-derived
threshold. They are not full-pipeline uncertainty estimates and do not include
model-refitting or threshold-reselection uncertainty. Threshold stability
resamples Calibration episodes only.

## Interpretation and limitations

- Robust MAD has the strongest aggregate Evaluation metrics here, but alerts
  on 55.6% of benign-control active-exercise samples and 100% of recent
  active-exercise samples. It is not selected.
- Temporal averaging increases recall and exercise-associated alerts.
  Episode-level alert rates remain distinct from sample-level rates.
- The illustrative 5% threshold is derived from Calibration baseline scores;
  its Evaluation FPR is not forced to 5%, unlike estimating and evaluating a
  threshold on the same samples.
- Results reflect synthetic simulator behavior, repeated correlated samples,
  artificial label construction, and a hand-set exercise response contrast.
  They establish no clinical suitability, causation, or flight readiness.
- The historical baseline artifact was unavailable; its metrics were not
  reproduced. The malformed historical seed-42 dataset and prior 780-sample
  result were not used.
- Final Test was not accessed. There is no final model or threshold decision.
  `B_max` and `E_max` remain blocked pending approval.

No candidate is advanced as a final choice. The robust detector remains a
research comparator; further review is needed before any later validation or
threshold decision. Do not make a production-readiness claim from these
results.

## Reproduction

From PowerShell:

```powershell
Set-Location C:\path\to\CAREYONDA\backend
$env:PYTHONPATH = 'C:\path\to\CAREYONDA;C:\path\to\CAREYONDA\backend'
& .\.venv\Scripts\python.exe ..\simulator\research\model_b_challenger_experiments.py
& .\.venv\Scripts\python.exe -m pytest -q tests\unit\test_model_b_challenger_experiments.py
& .\.venv\Scripts\python.exe -m ruff check ..\simulator\research\model_b_challenger_experiments.py tests\unit\test_model_b_challenger_experiments.py
& .\.venv\Scripts\python.exe -m ruff format --check ..\simulator\research\model_b_challenger_experiments.py tests\unit\test_model_b_challenger_experiments.py
```

The research script reads Training and Validation only and writes
`datasets/synthetic/model_b_part3_20261114/challenger_experiments/results.json`.
It does not load or inspect Final Test.
