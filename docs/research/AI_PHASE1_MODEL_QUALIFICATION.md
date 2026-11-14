# Phase 1 AI research qualification

Assessment date: 2026-11-14. Status: **owner review required; no commit or push**.
This is research qualification for the exact uses below, not clinical, behavioral-health,
NASA operational, safety, or real-time validation. No algorithm, API, frontend, M2 ranking,
M4.2 contract, artifact, or canonical policy was changed. No training occurred.

## Assessment identity and boundaries

Requested research baseline: `31887bc812411a563833e775ccb3320b7cc59ea7`.
The requested branch already existed at demo freeze
`2b073fcfe63a53c9af02ea048501f5c19faeae7b`. The owner explicitly selected reusing
that branch/base rather than creating a new branch at AI-I3. The qualification
worktree is `CAREYONDA-ai-qualification`, branch `feature/ai-model-qualification`.
The clean temporary checkout was preserved at the same detached commit because
Git worktree move cannot cross the /tmp and /home filesystems. No history was rewritten.
The research modules are inherited from AI-I3; the later base adds Model C application
wiring and presentation fixes. Consequently the full regression count is 796, not 751.
The demo-freeze and Replit branches were not modified or merged.

## Qualification decisions

| Component | Verdict | Exact qualified use and evidence | Excluded claim / condition |
| --- | --- | --- | --- |
| Model A v1.1.0 | CONDITIONALLY_QUALIFIED | Offline ranking of RR-1 ISS environmental windows; pinned artifact loaded, all 12,087 rows rescored, chronology and lineage verified | No labeled detection accuracy, human exposure linkage, prospective availability or unseen-mission generalization; threshold is an unapproved review convention |
| Model B v1.0.0, local enhanced artifact | CONDITIONALLY_QUALIFIED | Synthetic retrospective score research through canonical v2; 780 held-out outputs reproduced; unassessed default verified | Ahmed must approve a named canonical policy before decisions; no real-person or independent-seed qualification; not the unavailable original published refit |
| Model C v1.1.0 | QUALIFIED_FOR_RESEARCH | Deterministic within-person sleep deviation and descriptive fatigue counts with explicit scope, temporal support and abstention | Not a trained isolation/confinement detector; real application parameters require separate scientific review |
| AI-H1 | QUALIFIED_FOR_RESEARCH | Temporal pattern analysis under explicit metric/unit/source/window policies; synthetic boundary, gap, missingness and availability regressions | Policies are caller-supplied research conventions, not validated physiological cutoffs |
| AI-H2 | QUALIFIED_FOR_RESEARCH | Scope-compatible, provenance-traced research evidence association around unchanged M2 outputs | Not a clinical causal engine, probability model, validated joint A/B/C detector or safety engine |
| AI-H3 | QUALIFIED_FOR_RESEARCH | Frozen synthetic contract/evaluation harness; exact report reproduced | Finite post-implementation challenge, not blind external model-performance validation |
| AI-I3 | QUALIFIED_FOR_RESEARCH | Explicit adapters retaining native findings, lineage, missingness and eligibility; research demonstration reproduced | Historical replay quarantined; B context-only/unassessed; C fatigue context-only; no arbitrary direct model-to-hazard coercion |

The qualification of reasoning components concerns their documented deterministic
software/research functions. It is not qualification on real astronaut outcomes.
No component has demonstrated medical or operational validity. There is insufficient
evidence for A anomaly-detection sensitivity/specificity and B real-person performance;
those unsupported uses are outside these verdicts, not silently approved.

## Architecture and methods

Acquisition, feature extraction, inference, association and safety remain separate.
A and B use 200-tree seeded Isolation Forests, `-score_samples`, higher meaning more
statistically atypical, never probability. Both preserve feature order, original
missingness and training-fitted preprocessing; neither uses its score as diagnosis.

A uses 16 environmental predictors: current value, trailing 30-minute sample-weighted
mean, delta, count and missing indicator for CO2 ppm, temperature degC and humidity %,
plus gap seconds. Identifier/event columns are not predictors. Structural delta/gap
blanks are training-median imputed; missing primary value/mean causes abstention.
No scaling is applied. A flags inclusively, `score >= cutoff`.

B uses the exact 16-feature canonical order: heart-rate latest/missing/mean
(bpm/1/bpm); cabin CO2 partial-pressure latest/missing/mean (Pa/1/Pa); sleep
latest/missing/mean (h/1/h); fatigue latest/missing (1/1); communication delay
latest/missing/mean (s/1/s); exercise latest/missing (1/1). Fatigue/exercise encodings
are generator conventions, not validated health scales. Fitted median imputation,
no scaling, seed 42, effective max_samples 180 are retained. The verified experiment
uses strict `score > cutoff`; equality is not flagged. Canonical inference without
an approved policy emits score with `status=unassessed` and null flag.

C uses per-person daily bin medians and a reference median/raw MAD. Its absolute
raw-MAD distance is not a z-score, calibrated probability or severity. Flat, sparse,
stale, unavailable or incompatible baselines cause explicit limitations/abstention.
Fatigue remains ordered category counts, without numeric risk conversion. Target
support must fit assessment, not overlap reference or extend beyond assessment,
independently of arrival-time availability. Reference coverage/gap defaults are
unvalidated research parameters, not medical limits.

H1 validates evidence and detects configured temporal patterns. H2 associates
compatible evidence while retaining contradictions, abstentions and unchanged M2.
I3 retains full native records: environmental replay is not prospective evidence;
Model B cannot become an environmental sidecar; Model C sleep reaches H1 only via
an explicit matching policy, and fatigue remains contextual. Safety is not evaluated.

## Exact artifact identities and integrity

Only the previously trusted pinned local bundles were deserialized, after digest,
metadata, dataset and runtime verification. Unknown/ZIP artifacts were not loaded.
Hashes establish consistency with trusted local delivery, not cryptographic NASA
source authentication or proof of medical validity.

| Item | SHA-256 |
| --- | --- |
| A `model.joblib` | `f6b28b9d2e5925d0a568eba79bb0d3af516e31a8cbc7d96725ef86dfd85c44b6` |
| A metadata | `4f24c52ba0fbb4f26077399f27a4f8c46a5d3ca2d866949f0468560fc8118c93` |
| A evaluation | `7a96bdebe76c11abb6649ccd30455fc7d87a0ae08f076513d9b59f3c643ad752` |
| A dataset manifest | `40005d13160fdf2ea729237f965508fd2864ac1e187a3dcf8753f7cdf928706b` |
| A feature schema | `2c9b73e7372fdc6351265cc6ca502b17250c0ae893522fb4b1067a2fb4956da8` |
| B `model_b_pipeline.joblib` | `c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e` |
| B artifact manifest | `2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132` |
| B original metadata | `6271326b7335ec8f7d6d6934e39a0dba4cf02edaf5032149c8bcd7ba1680656d` |
| B dataset manifest | `22eb3c7ccf9ca6017ee63e4987dc93f6cacb107fab91e050313bd5b16e776649` |
| B feature schema | `fc0e4db42f1cb92b2230c24fb91fa112738b36d98f4ef3c4bb334201fed8cc69` |

A: `careyonda-model-a-nasa-rr1-environment-iforest`, version `1.1.0`, bundle
`CAREYONDA-Omar/artifacts/model_a/nasa_rr1_iforest_v1.1.0_rs42/`.
Metadata pins its estimator and processed-data manifest; no separate artifact-directory
manifest covering every A sidecar exists. Both evaluation and metadata hashes above
were recorded during this audit; they are not claimed as earlier signed delivery pins.
The dataset manifest's ten covered payload hashes passed. Training source matches
Omar commit `e86cda00fac8bb359164173d8d24ed0bf2f7aa90`, module
`app/training/nasa_environment_model_a.py`, SHA-256
`74540d0e563e4a9cacecbcf99107d68aae48e51869bc683c9b6b24fbb174f923`.

B: `model-b-synthetic-isolation-forest`, version `1.0.0`, bundle
`CAREYONDA-model-b-integration/artifacts/model_b/seed42-q95-final/`.
All five artifact-manifest payloads and six dataset payload hashes passed. Its five
training/source hashes match the preserved local implementation, including training
and data-loader modules. That source is an identified uncommitted local enhancement,
not identified by its worktree HEAD alone. The assembly contains the compatibility
loader/inference contract, not these original training modules. Ahmed's original
published all-baseline artifact remains distinct and unavailable. The uncovered
`inference_smoke.json` is not treated as independent integrity evidence.

B v1 metadata is translated in memory to v2 digest
`491d19a612d5aad4a9cbffda81e2f9e5e8250be69dc8ba13f3b7ccfc48b4a3a1`.
No migration, repackaging or artifact write occurs. The trusted loader checks exact
Pipeline/imputer/forest shape, medians, feature count, fitted trees and parameters.

Tested runtime: Python 3.12.10, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.1,
joblib 1.6.0. Exact numerical versions match recorded requirements. A was originally
recorded on Windows 11; this verification is local Linux inference, not a guarantee
of bit-identical retraining across platforms. No packages were installed.

## Dataset provenance and leakage assessment

A data: `datasets/processed/nasa_rr1_eda_d2d3_validated/`, generated from the three
local RR-1 EDA CSVs. All three raw CSV hashes match stored source/audit records.
The original copies were reported as manually exported from NASA EDA; an original
download timestamp, release identifier and signed/source-authenticated download log
are not established. Do not invent them. `Controller_Time_GMT` is interpreted as
UTC+00:00 with its original tokens retained. No independently verified source
ingestion time exists. These are ISS experiment-environment observations, not paired
human physiology. Typed feature references have spacecraft scope NASA-RR1/ISS;
ground-control measurements remain separate, not astronaut/compartment attribution.

Actual raw audit counts are 12,087 telemetry and 39 radiation records, differing
from the earlier request's 12,086/38. Forty-five comparable summary statistics match
at printed precision; one accumulated-dose comparison is unit-ambiguous. Radiation
is excluded from Model A; ambiguous accumulated units are not resolved by inference.

A split counts: train 8,460; validation 1,813; test 1,814. Verified strict event-time
ordering, unique/disjoint sample IDs and train.end < validation.start < test.start.
Trailing windows reset at split boundaries. All **652,332** feature-evidence
references resolve to matching-metric ISS evidence at or before sample time and
inside its split: zero future or cross-split references. Their source ingestion
timestamps are unknown. Preprocessing medians and q99 cutoff match training-only
values. No leakage was observed in these checked boundaries; this is not a universal
proof against unexamined provenance or selection bias. Adjacent windows remain
correlated; single-mission historical evaluation is not prospective validation.

B data: `datasets/synthetic/m1_2_seed42/`, 960 samples, 32 episodes, 5,760 observations,
16 predictors, seed 42; 240 samples per scenario. Synthetic exposure/response
relationships and scenario assignments are generator assumptions, not human medical
truth. Features exclude labels; labels are joined by sample ID only to select
baseline training episodes and evaluate proxies. Event-time windows/lineage are
reconstructed by the canonical trusted smoke runner.

Final B artifact is fold 0: six baseline episodes / 180 rows train; 26 disjoint
episodes / 780 rows hold out (two baseline, eight each other scenario). Both sample
and episode intersections are empty. All training labels are baseline. Four grouped
folds have disjoint training/holdout episodes, but use lexicographic episode-ID
striding, **not chronological train/test separation**. These episodes may overlap
in calendar time; they are synthetic independent contexts, not a prospective trial.
Only eight baseline episodes, one seed, shared generator assumptions and correlated
within-episode windows limit effective independent evidence. Prior exploratory
candidate reuse may introduce selection optimism; no sealed unseen-seed validation
is established. Do not confuse the local q95 experiment with the separate Part 3/4
Train/Calibration/Final-Test proposal, whose selection budgets remain unapproved.

## Model A measurements

Recomputed using the pinned fitted detector only, with fitting blocked:

| Split | Scored | Flagged at recorded q99 | Abstained | Imputed rows | Mean score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 8460 | 85 (1.0047%) | 0 | 2 | 0.4058145621 |
| Validation | 1813 | 0 | 0 | 1 | 0.4019113852 |
| Test | 1814 | 0 | 0 | 1 | 0.3887959224 |

Recorded cutoff: **0.5736639144466789**, inclusive comparison. Saved counts, means,
standard deviations, imputation counts and all saved top-score entries reproduced
within absolute/relative 1e-12. Maximum top-score difference was 1.11e-16 (validation),
zero on train/test. All rows repeated exactly within this runtime. Historical per-row
scores are not all supplied in the A bundle, so this is not a claim of comparing
12,087 individual saved predictions. A synthetic missing-main-reading perturbation
correctly abstained with null score/flag; missingness was not treated as normality.

No labeled A detection precision, recall, F1, AUROC, false-positive rate or false-negative
rate is identifiable. Zero later flags is not proof of zero anomalies or safety.
The source evaluation reports seed-7/1234 test rank correlations 0.987727/0.975591;
these are **reported, not refitted/reproduced here**. The research analysis runner
fits alternate forests for seed sensitivity, so it was deliberately not executed.
Its causal persistence, gap recovery, absent-threshold and manifest checks were
instead exercised with the existing synthetic research tests.

Recorded training-derived cutoff sensitivity, same pinned estimator and inclusive rule:

| Training q | Cutoff | Train / validation / test flags |
| --- | ---: | --- |
| .95 or .975 | 0.5518478834907368 | 469 / 1 / 2 |
| .99 | 0.5736639144466789 | 85 / 0 / 0 |
| .995 | 0.591397304155808 | 43 / 0 / 0 |
| .999 | 0.6281871262750673 | 9 / 0 / 0 |

Ties and a 309-row identical-feature run affect empirical quantiles; nominal tail
fractions are not achieved exactly. Training data is not certified anomaly-free.
Isolation Forest scores can saturate outside training support; score magnitude is
not severity. No unseen-mission, sensor-change or labeled extreme-event performance
has been established.

## Model B measurements

All 780 saved holdout scores and experimental strict-q95 flags reproduced exactly:
maximum absolute score difference **0.0**, tolerance absolute/relative 1e-12. Original
pipeline and canonical preprocessing/forest paths agree. Four partially imputed
samples retained exact imputation lists. All 780 canonical findings remain
**unassessed with null flags**, including when the unapproved experimental policy
is supplied as context. A new factual local read/acquisition receipt is used only
for this verification; it is not a backfilled historical arrival and is not published.

Existing recorded statistics independently recomputed from saved predictions:

| Evaluation | Samples | TN / FP / FN / TP | Precision | Recall | F1 | AUROC | AP |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| Pinned final artifact holdout | 780 | 58 / 2 / 327 / 393 | .994937 | .545833 | .704933 | .933796 | .993563 |
| Four-fold OOF saved records | 960 | 215 / 25 / 324 / 396 | .940618 | .550000 | .694128 | .852917 | .931993 |

Positive proxy = any nonbaseline scenario, including recent exercise. Final baseline
false-alert fraction = 2/60 = 3.3333%; OOF = 25/240 = 10.4167%. Final scenario flag
fractions: elevated CO2 209/240 (87.0833%); sleep deprivation 159/240 (66.25%);
recent exercise 25/240 (10.4167%). Those exercise non-flags are false negatives
only under the experiment's nonbaseline-proxy convention, not missed illnesses.
The high precision/AP reflects a heavily positive-enriched, generator-defined task.
Rows are not independent subjects; these are not clinical sensitivities.

The saved exercise-as-benign interpretation changes the final confusion matrix to
TN=273, FP=27, FN=112, TP=368, precision .931646, recall .766667, F1 .841143,
AUROC .925021, AP .937421; benign baseline/exercise flag fraction 9%. This is an
alternative synthetic label convention, not clinical adjudication. OOF statistics
were recomputed from saved records, not by refitting four forests. Pooled OOF score
rank metrics span differently fitted forests and are not calibrated across folds.

Additional **descriptive, unapproved counterfactual** threshold sensitivity:
cutoffs use only the original fitted model's 180 training-baseline scores with
NumPy higher, strict comparison; no threshold is selected or activated.

| Training q | Cutoff | FP / FN | Precision | Recall | F1 |
| --- | ---: | --- | ---: | ---: | ---: |
| .90 | .5205176007145814 | 3 / 215 | .994094 | .701389 | .822476 |
| .95 (recorded experiment) | .5403282173064036 | 2 / 327 | .994937 | .545833 | .704933 |
| .99 | .6210324062845743 | 0 / 716 | 1.000000 | .005556 | .011050 |

This tradeoff illustrates why stored thresholds are not automatic approval and why
holdout performance must not select a new cutoff. Named published offset, inclusive
calibration and strict training-quantile policies remain distinct. Ahmed's approval,
and any protocol-required alert budgets, remain outstanding. All-missing abstention,
partial imputation, lineage/identity/future-availability rejection and exact equality
are covered by existing synthetic contract tests. Only four imputed holdout samples
are observed here; no broad missing-not-at-random or real-person OOD robustness is
established. No independent-seed or real-health generalization claim is qualified.

## Statistical reasoning and Hybrid evaluation

Focused research suite: **284 passed** (A research, B v2/compatibility, C, temporal,
Hybrid, environmental contexts and adapters). Tests cover flat/sparse/stale baseline,
quality/missingness, interval ordering and support, cross-subject/mission/source
rejection, unknown/future availability, contradiction and abstention preservation.
The full backend suite additionally verifies the restored Model C local interface;
no API behavior was modified by this assessment.

Frozen H3 report matches checked-in JSON exactly: 13 challenge cases, 12 eligible,
one boundary rejection; 12/12 M2 invariance; 12/12 temporal recognition, evidence
association and abstention correctness; 1/1 contradiction case; 56/56 provenance
references resolved; zero unsupported directional assertions; deterministic output
13/13 for each ablation. H3 A/B/C are ablation configurations, **not Models A/B/C**.
Development cases are excluded from challenge metrics. The challenge is explicitly
post-implementation, pre-specified contract evaluation, not blinded external validation.

I3 synthetic demonstration reproduced: compatible Hybrid evidence supported;
cross-subject result abstained with zero usable observations; historical replay
ineligible with `historical_replay_not_prospective`; B unassessed/context-only;
C categorical fatigue context-only; future support excluded; M2 unchanged. A/B/C
statistical scores are not summed, calibrated into medical probabilities or used to
invent causal attribution. Caller declarations still require a trusted acquisition
boundary for future actual applications; software validation is not source authentication.

## Verification and reproducibility limits

- Full backend: **796 passed, 9 skipped, 1 deselected**. Estimator fitting was blocked
  by an external verification guard. Six B fit tests remain opt-in; one A fitting test
  was deselected. Optional NASA/replay fixtures and the unavailable original B artifact
  test remain skipped; the pinned local artifacts were checked separately above.
- Ruff lint/format passed (122 formatted files); strict mypy passed (116 files,
  including the Model A research script); existing dependency consistency passed.
- Frozen H3 JSON exact; adapter demonstration reproduced; no source code changed.
- Fitted A/B files are unchanged. No metadata/evaluation output or receipt is written
  into a repository. Reproducible inference is established for these bytes/runtime;
  deterministic retraining, alternative seeds and external generalization are not
  newly established. The original training entrypoints are not packaged in this
  assembly; their pinned/hashed external sources must be retained for a later
  separately authorized training-reproduction task.

From backend with separately provisioned research/dev dependencies:

```sh
python -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
python -m ruff check --no-cache . ../simulator
python -m ruff format --check --no-cache . ../simulator
python -m mypy
python -m pip check
PYTHONPATH=.:.. python -m examples.ai_h3_evaluation
PYTHONPATH=.:.. python -m examples.research_adapter_demo
```

Do not enable opt-in fitting tests. The executed tests additionally used a local
no-training guard; it is not a new dependency or research module. Compare H3 JSON
semantically with `docs/research/AI_H3_RESULTS.json`. PowerShell PYTHONPATH is `.;..`.
B trusted reproduction (set environment paths to the protected original bundle/data):

```sh
python -m app.storage.model_b_smoke \
  --artifact "$MODEL_B_ARTIFACT_DIR" --dataset "$MODEL_B_DATASET_DIR" \
  --expected-artifact-sha256 c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e \
  --expected-manifest-sha256 2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132 \
  --trusted-local-artifact
```

A reproduction uses `load_model_a` only on the trusted pinned bundle, then
`score_records(list(csv.DictReader(...)))` for each manifest-verified split,
repeating scoring and comparing counts/means/std/top entries to `evaluation.json`.
Before deserialization verify the exact model digest above, all dataset manifest
hashes and numerical runtime. Do not run the analysis CLI as a no-training smoke:
it intentionally fits alternate-seed forests. All individual and derived evaluation
files stay local; only aggregate research results are documented here.

## Blockers, proposed owners and Phase 2 entry requirements

| Priority / blocker | Responsible reviewer | Required evidence before expansion |
| --- | --- | --- |
| B canonical contract/policy approval | Ahmed / project research owner | Explicit approval reference for the exact artifact and named comparator/derivation, or explicit acceptance of unassessed operation; no inferred approval |
| Independent performance qualification | Omar for A; Ahmed for B | A independently adjudicated environmental events or a defined ranking-review study; B sealed independent seeds/episodes and defined benign-exercise controls; predeclared operating criteria |
| Training provenance/reproduction packaging | Artifact owners | Preserve exact hashed training source, environment and manifests; distinguish original B delivery from local enhanced bundle; separately authorize any retraining |
| Factual availability and source trust | Data/integration owner | Verified acquisition workflow/receipts and exact subject/mission/dataset/source identity; unknown historical source ingestion must remain unknown |
| Scientific monitor/policy validity | Research owner | Review C sampling/reference defaults and H1/H2 association conventions for each proposed data context; no universal physiological boundaries implied |
| Safety/operational use | Project safety owner | Separate authoritative reviewed safety policies and appropriate external validation; not provided by this qualification |

Next actions: review this report; resolve B approval while retaining unassessed default;
freeze an independent evaluation protocol and asset/source inventory; only then
separately authorize Phase 2 controlled research integration under explicit scope and
availability rules. No need or authorization for retraining has been inferred.
No real-time execution, public model endpoint or further milestone is started.
