# CAREYONDA Model B Part 4 — Candidate Evaluation and Selection

Status: research decision based only on the saved Part 3 results. No experiment
was run, no model was retrained, and no Final Test data was accessed. All
reported performance is exploratory, not independent confirmatory evidence.

## Executive decision

**Reject adoption of all nine challengers for now. Retain the original Model B
as the recommended decision; no new candidate, configuration, or threshold is
approved.** This is a conservative decision under unresolved requirements, not
a finding that the original model has demonstrated acceptable performance.

The Evaluation subset has already been used to compare candidates. In addition,
the required numeric `B_max` and `E_max` budgets remain unapproved. Therefore
the protocol's feasible-threshold rule cannot be applied, no candidate can be
shown to meet the constraints, and no final threshold or model can be selected.
The Calibration-95th-percentile operating points below are exploratory
comparisons only.

The existing Part 3 results report no historical baseline artifact and do not
reproduce historical metrics. This report does not modify or replace a
baseline artifact.

## Evidence and evaluation population

| Subset | Episodes | Samples | Per-scenario episodes / samples |
|---|---:|---:|---:|
| Training | 500 | 15,000 | 100 / 3,000 |
| Calibration | 75 | 2,250 | 15 / 450 |
| Evaluation | 75 | 2,250 | 15 / 450 |

Calibration and Evaluation were deterministically split by whole episode and
stratified by scenario. The saved results report zero overlap in episode,
sample, observation, and evidence-observation IDs. Evaluation comprises 15
episodes and 450 samples in each of: baseline, benign exercise control,
elevated CO2, recent exercise, and sleep deprivation. Positive proxy prevalence
is 1,350/2,250 (60%). Active-exercise alert-rate denominators are 225 samples
for benign exercise control and 225 for recent exercise.

The proxy mapping is baseline and benign exercise control = negative; elevated
CO2, recent exercise, and sleep deprivation = positive. These are synthetic
scenario proxies, not clinical ground truth. Recent exercise is reported
separately as a positive scenario and is not included in benign-control false
positives.

## Candidate comparison

All rows below use each candidate's exploratory threshold equal to its
Calibration baseline-score empirical 95th percentile. Thresholds were applied
to Evaluation; they were not selected or tuned on Evaluation. Counts are shown
as numerator/denominator for alert rates and as episodes with any alert / 15
for episode alert rates. Scenario recall order is elevated CO2 / recent
exercise / sleep deprivation. Episode-rate order is baseline / benign control /
elevated CO2 / recent exercise / sleep deprivation. The detector setup
parameters are those recorded in the existing results JSON.

| Candidate | Configuration | Precision | Recall | F1 | PR-AUC (average precision) | Scenario recall | Baseline FPR | Benign active alerts | Recent active alerts | Episode alerts (B / BC / CO2 / R / S) |
|---|---|---:|---:|---:|---:|---|---|---|---|---|
| Reference IF 200 | Isolation Forest: 200 trees, 256 samples, all features, seed 42 | 0.851 | 0.780 | 0.814 | 0.894 | 1.000 / 0.576 / 0.764 | 21/450 (0.047) | 114/225 (0.507) | 134/225 (0.596) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 500 trees | 500 trees, 256 samples, all features, seed 42 | 0.868 | 0.745 | 0.802 | 0.903 | 1.000 / 0.447 / 0.789 | 16/450 (0.036) | 96/225 (0.427) | 105/225 (0.467) | 8/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 75% feature sampling | 200 trees, 256 samples, 75% feature sampling, seed 42 | 0.868 | 0.761 | 0.811 | 0.910 | 1.000 / 0.473 / 0.809 | 20/450 (0.044) | 91/225 (0.404) | 118/225 (0.524) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| IF 128 subsamples | 200 trees, 128 samples, all features, seed 42 | 0.858 | 0.741 | 0.795 | 0.883 | 0.996 / 0.458 / 0.771 | 25/450 (0.056) | 100/225 (0.444) | 108/225 (0.480) | 9/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Robust MAD distance | Training-baseline median/MAD distance; recorded fallback scale rules | 0.887 | 0.955 | 0.920 | 0.983 | 1.000 / 0.864 / 1.000 | 15/450 (0.033) | 125/225 (0.556) | 225/225 (1.000) | 11/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Without heart rate | Reference IF; removes `heart_rate_latest`, `heart_rate_missing`, `heart_rate_mean` | 0.945 | 0.506 | 0.659 | 0.888 | 0.544 / 0.044 / 0.929 | 20/450 (0.044) | 14/225 (0.062) | 10/225 (0.044) | 12/15 / 14/15 / 15/15 / 11/15 / 15/15 |
| Without exercise features | Reference IF; removes `exercise_active_latest`, `exercise_active_missing` | 0.894 | 0.669 | 0.765 | 0.897 | 0.947 / 0.273 / 0.787 | 11/450 (0.024) | 68/225 (0.302) | 73/225 (0.324) | 8/15 / 15/15 / 15/15 / 15/15 / 15/15 |
| Without both groups | Reference IF; removes heart-rate and exercise feature groups | 0.944 | 0.371 | 0.533 | 0.878 | 0.289 / 0.036 / 0.789 | 14/450 (0.031) | 11/225 (0.049) | 8/225 (0.036) | 10/15 / 12/15 / 15/15 / 11/15 / 15/15 |
| Causal 3-sample score mean | Mean of current and previous two reference scores; episode state reset | 0.853 | 0.847 | 0.850 | 0.908 | 1.000 / 0.682 / 0.858 | 11/450 (0.024) | 139/225 (0.618) | 158/225 (0.702) | 7/15 / 15/15 / 15/15 / 15/15 / 15/15 |

`B`, `BC`, `R`, and `S` denote baseline, benign exercise control, recent
exercise, and sleep deprivation. For positive scenarios, an episode with no
alert is a missed anomaly episode under the synthetic proxy. Thus the
without-heart-rate candidate missed 4/15 recent-exercise episodes; without
both groups missed 4/15 recent-exercise episodes; all other listed positive
scenario episode detection counts were 15/15. Episode detection means at least
one alert in the episode and does not imply adequate sample-level recall.

Precision, recall, F1, and scenario recall use the pooled Evaluation samples.
PR-AUC is average precision from continuous scores. No PR-AUC confidence
interval is present in the saved results.

## Available episode-bootstrap intervals

The following are saved 95% percentile intervals from 1,000 episode-bootstrap
replicates (seed 4243), resampling Evaluation episodes within scenario. Metric
intervals condition on the already-fitted model, fixed Evaluation scores, and
the fixed exploratory Calibration threshold. They do not capture refitting,
candidate-selection, or threshold-reselection uncertainty. Scenario recall
order is elevated CO2 / recent exercise / sleep deprivation. Episode-rate
interval order is baseline / benign control / elevated CO2 / recent exercise /
sleep deprivation. Values are rounded to three decimals.

| Candidate | Precision / recall / F1 intervals | Scenario-recall intervals | Baseline FPR / benign-active / recent-active intervals | Episode-alert-rate intervals |
|---|---|---|---|---|
| Reference IF 200 | 0.822–0.878 / 0.758–0.803 / 0.794–0.833 | 1.000–1.000 / 0.520–0.627 / 0.724–0.804 | 0.024–0.076 / 0.427–0.600 / 0.511–0.680 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 500 trees | 0.839–0.895 / 0.724–0.766 / 0.784–0.819 | 1.000–1.000 / 0.402–0.484 / 0.744–0.833 | 0.013–0.064 / 0.351–0.516 / 0.387–0.542 | 0.267–0.733 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 75% feature sampling | 0.840–0.893 / 0.736–0.787 / 0.791–0.830 | 1.000–1.000 / 0.413–0.529 / 0.762–0.856 | 0.029–0.060 / 0.333–0.480 / 0.431–0.618 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| IF 128 subsamples | 0.826–0.887 / 0.715–0.767 / 0.775–0.815 | 0.987–1.000 / 0.400–0.511 / 0.722–0.820 | 0.022–0.096 / 0.369–0.525 / 0.404–0.560 | 0.333–0.867 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Robust MAD distance | 0.851–0.916 / 0.927–0.982 / 0.894–0.941 | 1.000–1.000 / 0.780–0.947 / 1.000–1.000 | 0.020–0.049 / 0.422–0.702 / 1.000–1.000 | 0.533–0.933 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Without heart rate | 0.933–0.956 / 0.483–0.530 / 0.638–0.680 | 0.480–0.607 / 0.027–0.064 / 0.904–0.951 | 0.031–0.058 / 0.040–0.089 / 0.022–0.071 | 0.600–1.000 / 0.800–1.000 / 1.000–1.000 / 0.467–0.933 / 1.000–1.000 |
| Without exercise features | 0.869–0.916 / 0.648–0.690 / 0.749–0.782 | 0.911–0.976 / 0.238–0.309 / 0.747–0.822 | 0.011–0.038 / 0.244–0.369 / 0.267–0.378 | 0.267–0.800 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |
| Without both groups | 0.928–0.959 / 0.351–0.393 / 0.511–0.556 | 0.240–0.344 / 0.020–0.053 / 0.758–0.818 | 0.018–0.044 / 0.031–0.067 / 0.018–0.058 | 0.400–0.867 / 0.600–1.000 / 1.000–1.000 / 0.467–0.933 / 1.000–1.000 |
| Causal 3-sample score mean | 0.825–0.878 / 0.820–0.873 / 0.829–0.869 | 1.000–1.000 / 0.624–0.742 / 0.807–0.907 | 0.009–0.042 / 0.533–0.707 / 0.618–0.782 | 0.200–0.733 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 / 1.000–1.000 |

The saved threshold-stability results are bootstrap intervals for the
Calibration baseline empirical 95th-percentile score, shown as lower bound /
median / upper bound. These are descriptive score-threshold distributions,
not the protocol's feasible-threshold-selection stability analysis; values
across different candidates are not directly comparable.

| Candidate | Calibration q95 threshold distribution |
|---|---|
| Reference IF 200 | 0.5320 / 0.5405 / 0.5511 |
| IF 500 trees | 0.5271 / 0.5397 / 0.5518 |
| IF 75% feature sampling | 0.5322 / 0.5393 / 0.5501 |
| IF 128 subsamples | 0.5355 / 0.5491 / 0.5594 |
| Robust MAD distance | 0.9909 / 1.0333 / 1.0583 |
| Without heart rate | 0.5380 / 0.5421 / 0.5535 |
| Without exercise features | 0.5302 / 0.5487 / 0.5520 |
| Without both groups | 0.5519 / 0.5587 / 0.5654 |
| Causal 3-sample score mean | 0.5221 / 0.5398 / 0.5496 |

PR-AUC bootstrap intervals are unavailable. The Part 3 results also do not
report a feasible-resample fraction or an IQR from repeatedly applying the
protocol's constrained threshold-selection rule. No such quantities are
inferred here.

## Scenario-specific error analysis

### Baseline false positives

At the exploratory Calibration q95 operating point, sample false-positive
counts ranged from 11/450 (0.024; without exercise features and temporal
averaging) to 25/450 (0.056; IF 128 subsamples). The robust MAD detector had
15/450 (0.033), while the reference IF had 21/450 (0.047). Episode-level
baseline alert rates ranged from 7/15 for temporal averaging to 12/15 for
without-heart-rate ablation; the reference IF alerted in 11/15 baseline
episodes. A low sample FPR did not imply few episodes with any alert.

### Benign exercise alerts and recent exercise behavior

Benign-control active-sample alert rates ranged from 11/225 (0.049; without
both feature groups) to 139/225 (0.618; temporal averaging). The robust MAD
candidate flagged 125/225 (0.556), and the reference IF flagged 114/225
(0.507). All candidates except the two ablations without heart rate or both
groups alerted in all 15 benign-control episodes.

Recent-exercise active-sample alert rates ranged from 8/225 (0.036; without
both groups) to 225/225 (1.000; robust MAD). The reference IF rate was
134/225 (0.596). These are descriptive positive-scenario alert rates; they
are not benign-control false-positive rates. Recent-exercise sample recall
was 0.864 for robust MAD but only 0.044 without heart rate and 0.036 without
both feature groups. Robust MAD detected at least one sample in all
15/15 recent-exercise episodes, while the two ablations each missed 4/15.

### Missed anomaly episodes and feature ablations

At least one alert occurred in all 15 elevated-CO2 and sleep-deprivation
episodes for every candidate except IF 128 subsamples, which detected 14/15
elevated-CO2 episodes. Recent-exercise episode detection was 11/15 for each
heart-rate-removed ablation and 15/15 for the other candidates. Episode
detection can mask sparse misses: it is not equivalent to sample recall or
timely detection.

Removing heart-rate features reduced benign active alerts from the reference
114/225 to 14/225 and recent active alerts from 134/225 to 10/225, but
reduced pooled recall from 0.780 to 0.506, elevated-CO2 recall from 1.000 to
0.544, and recent-exercise recall from 0.576 to 0.044. Removing exercise
features alone reduced pooled recall to 0.669 and recent-exercise recall to
0.273. Removing both groups reduced pooled recall to 0.371 and
recent-exercise recall to 0.036. These ablations expose trade-offs; they do
not justify feature selection.

The report accompanying the results gives Evaluation active-sample
`heart_rate_latest` means of 86.11 for benign controls and 102.66 for recent
exercise (medians 85.87 and 102.43); corresponding Training means are 87.46
and 103.51. The hand-set half-amplitude heart-rate response for the synthetic
benign control versus full configured exercise response creates a potential
synthetic shortcut. It is not evidence that real benign exertion is
distinguishable from a health hazard.

### Threshold and operating-point limitations

Calibration q95 score thresholds are available with the descriptive
bootstrap distributions above. These intervals describe variation in the
estimated Calibration score quantile, not a threshold selected under both
approved alert budgets. The protocol's threshold-stability analysis requires
resampling episodes, repeating the constrained selection rule, and reporting
feasibility and constraint-pass fractions. That analysis cannot be completed
without numeric `B_max` and `E_max`, and is not present in the saved results.
No candidate can be called budget-compliant.

## Selection requirements and decision

The validation protocol requires numeric `B_max` and `E_max` to be specified
before validation is opened. Among thresholds satisfying both, it specifies
maximizing the unweighted macro-average of sample recall across elevated CO2,
recent exercise, and sleep deprivation, with stated tie-breakers. `B_max` and
`E_max` remain unapproved. The saved Part 3 operating points use Calibration
baseline q95 thresholds for comparison; they do not establish that the
protocol's constrained threshold search was performed for all thresholds and
candidates. A macro-recall-maximizing feasible threshold and feasible
bootstrap fraction are therefore unavailable, not inferred.

The Evaluation subset was used for candidate comparison and is not independent
confirmatory evidence. No candidate demonstrably satisfies the existing
selection requirements. Per the requested decision rule, **all challengers
are rejected for adoption at this stage and the original Model B remains the
recommended decision pending an approved, independent confirmatory evaluation**.
This does not certify the original Model B as safe, effective, or budget
compliant.

**Recommended configuration:** no new configuration is approved. The
reference IF and robust MAD results may remain research comparators; neither
is selected. No hyperparameter configuration or final threshold is endorsed.

## Leakage, limitations, and uncertainty

- The experiment separates scenario labels and identifiers from the feature
  matrix; the saved run records that labels were not used as features.
  Training-only preprocessing/model fitting, episode-disjoint subsets, and
  causal temporal ordering/reset behavior are documented in the script and
  Part 3 report. No direct label, scenario, ID, or metadata predictor leakage
  is reported.
- This is synthetic, event-time evaluation with repeated, correlated samples
  and only 15 Evaluation episodes per scenario. Bootstrap resampling is
  episode-based, but intervals condition on the fitted model, scores, and
  exploratory threshold; they do not capture end-to-end pipeline uncertainty.
- Candidate comparison on Evaluation creates selection optimism if the
  apparent winner is advanced. These results are exploratory and do not
  support clinical or operational claims.
- The fixed synthetic exercise-amplitude contrast is a potential shortcut.
  Ablation results are highly sensitive to removing heart-rate and exercise
  features, especially for recent-exercise recall.
- The available analysis does not report PR-AUC confidence intervals, a
  constrained threshold-selection result, a feasible-resample fraction, or
  the protocol-required threshold-selection bootstrap distribution.
- Numeric `B_max` and `E_max` remain unapproved. Final Test is reserved and
  was not accessed.
- Historical baseline metrics were not reproduced because the original
  baseline artifact is reported unavailable. The new challenger results do
  not replace it.

## Original baseline artifact preservation status

**Verified:** this Part 4 work creates only this report and does not overwrite
or modify an original baseline artifact. The Part 3 report and results JSON
state that the historical baseline artifact was unavailable and that
historical metrics were not reproduced.

**Unverifiable:** the existence, location, integrity, or preservation of any
original baseline artifact outside the reviewed Part 3 sources was not
independently checked. No claim is made that an artifact was found or
preserved beyond the fact that this task did not access or modify one.
