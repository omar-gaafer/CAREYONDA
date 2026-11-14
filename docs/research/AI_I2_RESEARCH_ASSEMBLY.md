# AI-I2 — Controlled AI research assembly

Status: **ready for a separately authorized AI-I3 integration task**, as a unified,
tested research codebase only. No joint clinical/operational pipeline, new adapters,
API routes or frontend functionality are claimed. AI-I2 made no commits or pushes; the final sprint separately authorizes this research checkpoint publication.

## Identity and source ancestry

Target worktree: `CAREYONDA-ai-research-assembly`; branch
`feature/ai-research-assembly`; HEAD remains the pinned Hybrid base. Source branches
were not merged, rebased, reset or switched. Every source descends from the shared
application checkpoint; A, B and C add separate changes to that checkpoint, while
the selected target already inherits AI-H1/H2/H3. No newer `main` or unrelated work
was imported. Exact commits:

| Source | Branch | Commit |
|---|---|---|
| Shared application | `feature/model-a-integration` | `1ebdd03a8b29239742074e3ac0bff247d8a5785b` |
| Model A research | `feature/ai-model-a-enhancement` | `bbd15972da9988c46cbdc85550bf4296f004f0f3` |
| Model B reconciliation | `feature/ai-model-b-reconciliation` | `74ea8b4bfbf5d3b14e352b598037161595cc772a` |
| Model C research | `feature/omar-model-c` | `aecc38f7461a5d61f9e5c415cd8d2d9ac985d151` |
| Hybrid base | `feature/ai-hybrid-enhancement` | `1bd07edaef9daf7eb192342dfb0d0d10a611f532` |

The Model C local remediation worktree remains on its older commit; assembly reads
Git objects at the specified newer source commit, not that working directory.
No uncommitted original development source was used as an implicit baseline.

## Included files and exact-byte preservation

39 imported files match their pinned source bytes exactly. The combined
`backend/pyproject.toml` is the only synthesized source/configuration file.
One final-sprint integration smoke file and two assembly documentation/inventory
files bring changes relative to the Hybrid base to **43 files**. Full paths and hashes are recorded in
`AI_I2_CHANGED_FILES.json`, including every deferred Model C path and all inherited
Hybrid research files. Included source files:

- `.gitignore` — source A.
- `backend/app/research/__init__.py` — source A.
- `backend/app/research/model_a_environmental.py` — source A.
- `backend/scripts/__init__.py` — source A.
- `backend/scripts/analyze_model_a_environmental.py` — source A.
- `backend/tests/unit/test_model_a_environmental_research.py` — source A.
- `backend/tests/unit/test_model_a_research_pipeline.py` — source A.
- `docs/architecture/MODEL_A_ENVIRONMENTAL_RESEARCH.md` — source A.
- `docs/architecture/MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V1.json` — source A.
- `docs/architecture/MODEL_A_ENVIRONMENTAL_RESEARCH_CONTRACT_V2.json` — source A.
- `backend/app/ai/anomaly.py` — source B.
- `backend/app/ai/baseline.py` — source B.
- `backend/app/ai/model_b_anomaly.py` — source B.
- `backend/app/schemas/model_b.py` — source B.
- `backend/app/storage/model_b_smoke.py` — source B.
- `backend/app/storage/model_b_store.py` — source B.
- `backend/app/storage/model_b_v1.py` — source B.
- `backend/requirements-model-b-resolved.txt` — source B.
- `backend/tests/unit/test_benign_exercise_control.py` — source B.
- `backend/tests/unit/test_model_b_challenger_experiments.py` — source B.
- `backend/tests/unit/test_model_b_inference_contract.py` — source B.
- `backend/tests/unit/test_model_b_reconciliation.py` — source B.
- `backend/tests/unit/test_model_b_v1_compatibility.py` — source B.
- `docs/architecture/MODEL_B_AUDIT.md` — source B.
- `docs/architecture/MODEL_B_BENIGN_EXERCISE_CONTROL.md` — source B.
- `docs/architecture/MODEL_B_VALIDATION_PROTOCOL.md` — source B.
- `docs/research/AI_I1_2_MODEL_B_ARTIFACT_VERIFICATION.md` — source B.
- `docs/research/AI_I1_MODEL_B_RECONCILIATION.md` — source B.
- `docs/research/MODEL_B_PART3_CHALLENGER_EXPERIMENTS.md` — source B.
- `docs/research/MODEL_B_PART4_CANDIDATE_EVALUATION_AND_SELECTION.md` — source B.
- `docs/research/MODEL_B_PART5_FINAL_DELIVERY_REPORT.md` — source B.
- `simulator/research/__init__.py` — source B.
- `simulator/research/benign_exercise_control.py` — source B.
- `simulator/research/model_b_challenger_experiments.py` — source B.
- `backend/app/ai/isolation_confinement.py` — source C.
- `backend/app/schemas/isolation_confinement.py` — source C.
- `backend/tests/unit/test_isolation_confinement.py` — source C.
- `docs/architecture/MODEL_C_HYBRID_COMPATIBILITY.md` — source C.
- `docs/architecture/MODEL_C_ISOLATION_CONFINEMENT.md` — source C.

## Shared-file review and resolutions

- **Dependency/tool configuration:** A and B both change `backend/pyproject.toml`.
  Started from the Hybrid file, retained its core/model-a/dev dependencies and all
  quality settings, added A's `model-a-research` extra and B's `model-b` extra,
  and added A's analysis script to strict mypy's default scope. Numerical pins are
  compatible and unchanged; no packages were installed or upgraded.
- **Shared AI placeholders:** B's published `app/ai/anomaly.py` and `baseline.py`
  replace empty shared-baseline placeholders. The current Hybrid code depends on
  `app/schemas/anomaly.py` and `baseline.py`, not those empty AI placeholders.
  Included the verified B source exactly; canonical B remains separately named
  `app/ai/model_b_anomaly.py`. No M4.2 contract or M2 ranking code was overwritten.
- **Ignore rules:** imported A's additive `/work/python312/` ignore entry exactly;
  existing protections for credentials, artifacts, caches and datasets remain.
- **Model C status document:** retained the shared status file rather than replacing
  it with a branch-specific application inventory. This report is the current
  assembly status; the older status document may not describe this research subset.
- **Hybrid preservation:** every inherited file outside the explicitly imported
  shared-placeholder/ignore/config set remains byte-identical to target HEAD.
  All 23 Hybrid research additions are preserved exactly, including the frozen
  challenge specification, result records and compatibility review.

No scientific conflict or compatibility correction was required. Algorithms,
threshold values, score directions, original contracts and expected test outcomes
were not altered. No source test was removed or weakened.

## Deferred Model C application components

All paths below are deliberately absent or retain their shared-baseline form.
They must be integrated as a coherent later application-composition change, not
inferred to be operational here:

- `backend/app/api/model_c.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `backend/app/application/model_c_local.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `backend/app/model_c_main.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `backend/app/schemas/model_c_local_entry.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `backend/tests/integration/test_model_c_api.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `backend/tests/unit/test_model_c_local_entry.py` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `docs/architecture/AI_IMPLEMENTATION_STATUS.md` — Keep baseline status document; assembly report describes selected research-only capabilities.
- `frontend/src/app/App.test.tsx` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/app/App.tsx` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/app/modules.ts` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/contracts/model-c.ts` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/features/model-c/ModelCPanel.tsx` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/features/model-c/application.ts` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/features/model-c/fixtures/synthetic-abstained.json` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/features/model-c/fixtures/synthetic-assessed.json` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/features/model-c/model-c.test.tsx` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.
- `frontend/src/infrastructure/model-c.ts` — Application composition deferred: transport/local-entry contracts and helpers, API tests, UI/fixtures and stale-response fix must be integrated together.

**Safety-critical deferral:** `ModelCPanel.tsx`'s verified request-generation guard
and its deferred-response regression tests are deferred together with the entire
Model C UI/client flow. The assembly does not expose the older unsafe Model C UI
or add its endpoint. Any later Model C UI import must use the pinned aecc38f source,
including Clear Session/participant/session invalidation and stale success/error/
loading rejection. Model C's independent temporal-support correctness fixes ARE
included in the research engine and exercised by its unit tests.
The shared baseline's existing Model A UI/API remains unchanged; no UI build is
claimed for Model C. Local-entry helper and API tests remain deferred with their
contracts and handlers, rather than copied as broken imports.

## Import paths and boundary status

| Component | Imports / executable entry | Scope |
|---|---|---|
| A research | `app.research.model_a_environmental`; `scripts.analyze_model_a_environmental` | Retrospective NASA environmental research; event contract v2 |
| A baseline service | `app.application.environmental_anomaly`; `app.schemas.environmental_anomaly_context` | Existing optional environmental sidecar; unchanged |
| B canonical | `app.schemas.model_b`; `app.ai.model_b_anomaly.ModelBService` | Synthetic v2 evidence/feature validation and policy-neutral scoring |
| B trusted compatibility | `app.storage.model_b_store`; `app.storage.model_b_v1`; `app.storage.model_b_smoke` | Explicit trusted local artifact checks; no automatic loading |
| B research utilities | `simulator.research.model_b_challenger_experiments` | Existing offline experiments; **not executed for training here** |
| C | `app.ai.isolation_confinement`; `app.schemas.isolation_confinement` | Deterministic sleep/fatigue monitor, not validated isolation detector |
| H1 | `app.ai.temporal_evidence`; `app.schemas.temporal` | Exact-source bounded prospective numeric evidence |
| H2 | `app.ai.research.hybrid`; `app.schemas.hybrid` | Descriptive association; immutable original M2 snapshot |
| H3 | `examples.ai_h3_evaluation` | Frozen synthetic contract challenge and capability ablation |

No Model B/C-to-Hybrid adapter is implemented by this assembly. H1/H2's model-context
input remains Model A-specific. B needs an explicitly reviewed context/availability
adapter; its retrospective acquisition receipt does not establish original source
availability. C sleep evidence requires reviewed numeric reference conventions;
categorical fatigue cannot be coerced into H1 numeric evidence, and C's score is not
an H1 pattern. C's model/method/instrument identity needs a preserved sidecar.

Model B remains **unassessed by default**. The recorded experimental q95 policy
retains `0.5403282173064036` and strict `>` only as explicitly verified artifact
configuration; no policy was approved or globally activated. No real artifact was
loaded, copied, modified or retrained during AI-I2. Prior local artifact verification
is documented in AI-I1.2; it is not relabelled as a fresh assembly smoke run.

## Combined verification

Verified with the existing isolated CPython 3.12.10 numerical environment and the
previously provisioned HTTP dependency overlay; no installation or fresh platform
resolution is claimed. Installed optional extras satisfy all combined declarations;
`pip check` found no broken requirements.

| Check | Result |
|---|---|
| Focused A/B/C/H1/H2/H3 tests, 14 files | **307 passed, 7 skipped** |
| Full relevant backend | **725 passed, 9 skipped, 1 deselected** |
| Ruff lint including scripts | Passed |
| Ruff formatting including scripts | Passed, 107 files |
| Strict mypy including A research script | Passed, 106 source files |
| Dependency consistency | Passed |
| Git whitespace and all new text files | Passed |
| Exact source/Hybrid preservation | Passed |

The no-training requirement is enforced during verification by an external test-run
guard that rejects any real IsolationForest.fit call. Six B fitting tests remain
opt-in and were not enabled. The original Model A fitting test is intentionally
deselected without editing it. Nine full-suite skips comprise those six B tests,
the original published Model B artifact integrity test, optional trusted Model A
replay, and optional local NASA CSV validation. The original published Model B
artifact remains distinct from the verified enhanced local B artifact. No trusted
artifact or NASA measurement files were copied merely to turn skips into passes.

## H3 reproduction

Re-executed `python -m examples.ai_h3_evaluation`; output stayed under the external
temporary directory and matched the frozen `AI_H3_RESULTS.json` **exactly as JSON**.
The baseline's stored output and specification were not overwritten.

- 13 challenge cases: 12 eligible, one expected boundary rejection.
- M2 invariance: 12/12 eligible cases.
- Deterministic reproducibility: 13/13 for each ablation configuration.
- Full configuration: association and abstention 12/12; contradiction 1/1;
  temporal recognition 12/12; provenance references resolved 56/56;
  unsupported directional assertions 0.

**H3 configuration labels A/B/C are ablation configurations, not the three trained
or deterministic models.** These results do not demonstrate cross-model fusion,
clinical validity or new model performance. The challenge is post-implementation,
pre-specified contract testing, not blind external validation.

## Reproduction instructions

Use the already provisioned compatible interpreter; set `RESEARCH_PYTHON` to it.
Run from `backend/`. If its HTTP dependencies are separately provisioned, expose
them through the approved environment or documented local dependency overlay.

```sh
"$RESEARCH_PYTHON" -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
"$RESEARCH_PYTHON" -m ruff check app tests ../simulator scripts
"$RESEARCH_PYTHON" -m ruff format --check app tests ../simulator scripts
"$RESEARCH_PYTHON" -m mypy
"$RESEARCH_PYTHON" -m pip check
"$RESEARCH_PYTHON" -m examples.ai_h3_evaluation > "$H3_TEMP_OUTPUT"
git diff --check
```

Set `H3_TEMP_OUTPUT` to an external temporary file, never a tracked results file.
Leave `CAREYONDA_RUN_MODEL_B_FIT_TESTS` unset. No baseline artifact test is turned
into a pass by using another model. The temporary no-training guard used for this
verification is a local execution control, not a source/dependency change.

## Scientific limits and next authorization

NASA RR-1 environment is not paired with synthetic astronaut physiology. Preserve
NASA concentration ppm, synthetic partial pressure Pa, astronaut/mission/source
identity, event time, ingestion and acquisition separately. No new conversion,
shared context, causal relationship, calibrated confidence or diagnosis is inferred.
Scores are statistical estimates; missingness is not normality. Safety procedures
and M2 ranking remain independent.

This candidate is ready for AI-I3 planning/implementation under separate scope,
not automatic publication or joint inference. Remaining requirements: owner approval
of Model B's contract/policy or explicit acceptance of unassessed outputs; explicit
model-specific adapter contracts with exact provenance/availability and scope;
reviewed C temporal conventions; and later coherent API/frontend composition that
includes all deferred safety fixes. Existing artifact provisioning remains optional,
offline and outside Git. All eight pre-existing worktrees and all inspected Model
A/B artifacts retain their original hashes/status/branch/HEAD. Source branches are not merged; publication is limited to the research assembly branch.


## Final sprint research checkpoint

Added only `backend/tests/integration/test_research_assembly_smoke.py` beyond the
reviewed AI-I2 assembly; no integration-blocking algorithm/source corrections were
needed. Eight acceptance checks pass: artifact-free imports of all research modules;
Model A spacecraft/environment context exclusion from astronaut evidence; Model B
scored-but-unassessed with no policy; Model C participant/mission preservation and
future-support rejection; Hybrid rejection of wrong mission and wrong subject;
historical NASA-labelled synthetic replay quarantine; and unchanged M2 results
before/after exercising all three research modules.

All release checks above were rerun in the final sprint. Frozen H3 output again
matches exactly as JSON. No trusted artifact was loaded or modified, no package
installed, and no actual model fitting occurred. Source bytes from the pinned
commits and inherited Hybrid/application code remain unchanged except the documented
shared configuration. No new API endpoint, frontend flow or cross-model adapter.

The canonical Model B threshold still requires Ahmed's approval. The recorded q95
configuration is not an activated default. Readiness is a verified joint research
codebase, not a joint clinical, causal or operational inference pipeline.

Exact no-training backend reproduction, from repository root in the compatible
provisioned Python environment (Python 3.12.10 used here):

```sh
cd backend
env -u CAREYONDA_RUN_MODEL_B_FIT_TESTS python -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
python -m pytest -q tests/integration/test_research_assembly_smoke.py
python -m ruff check app tests ../simulator scripts
python -m ruff format --check app tests ../simulator scripts
python -m mypy
python -m pip check
```

The six Model B fitting tests remain default-skipped; the inherited Model A fitting
test is explicitly deselected. Two trusted NASA/Model A data opt-ins remain skipped,
as does the distinct unavailable original-published Model B artifact integrity test.
Local enhanced Model B integrity and inference were verified in AI-I1.2, not reloaded
for this sprint. These exclusions are disclosed, not represented as passing tests.
