# Model A integration Phase 1

Implemented 2026-11-13 on local `feature/model-a-integration` in
`/tmp/CAREYONDA-model-a-integration`. Nothing was staged, committed or pushed.

## Baseline provenance

No committed baseline contains the current M2/M3/M4.2 work. This worktree starts at
`bfc19cbdeab9e71cb1ab16d4e62e954d2ef4969c` and overlays 27 original dirty backend,
README and architecture/API documentation files. The exact original hashes are in
[MODEL_A_BASELINE_SNAPSHOT.json](MODEL_A_BASELINE_SNAPSHOT.json). This is explicitly
an **uncommitted snapshot**, not a released baseline. Frontend work was not copied.
The source workspace's 71 dirty files and Git status were verified unchanged.
Copied baseline files remain byte-identical except the authorized dependency
addition to `backend/pyproject.toml`. M2/M3/M4.2 contracts, algorithms and routes are
unchanged. The branch has no new commits; baseline publication needs separate review.

## Integration files

Six files imported byte-for-byte from Omar commit
`e86cda00fac8bb359164173d8d24ed0bf2f7aa90`:

- `backend/app/ai/nasa_environment_anomaly.py`
- `backend/app/schemas/nasa_environment_model.py`
- `backend/app/storage/nasa_environment_model_store.py`
- `backend/requirements-model-a.txt`
- `backend/tests/model_a_fixtures.py`
- `backend/tests/unit/test_nasa_environment_anomaly.py`

New application/schema and focused tests:

- `backend/app/application/environmental_anomaly.py`
- `backend/app/schemas/environmental_anomaly_context.py`
- `backend/tests/environmental_context_fixtures.py` (shared artificial adapter fixtures)
- `backend/tests/unit/test_environmental_anomaly_context.py`
- `backend/tests/integration/test_environmental_anomaly_adapter.py`

Dependency configuration: Model A is an optional `model-a` extra in `pyproject.toml`;
existing FastAPI/Uvicorn declarations remain intact. The reviewed Model A pins are
unchanged. `backend/requirements-windows.txt` is imported from Omar's source commit
because the reviewed requirements include it. New
`backend/requirements-model-a-integration.txt` includes both the Model A and existing
M3 snapshots. No training module or training-dependent integration tests were imported.
Documentation comprises this report, baseline manifest and the example linked below.

## Public interface and semantics

```python
service = EnvironmentalAnomalyService(detector)  # injected detector protocol
contexts = service.assess(samples, assessed_at=aware_assessment_time)
# Explicit trusted-local-artifact opt-in; never an automatic startup load:
service = EnvironmentalAnomalyService.from_artifact(local_artifact_directory)
```

Each `EnvironmentalSample` has a NASA-RR1/ISS dataset/run/origin scope, original sample
ID, UTC event and availability times, transformation version, 16 ordered feature
values/units/observation-ID lists, and original observation snapshots. The service
requires real-source context, increasing unique times, unique sample IDs and a single
stream. Every observation must have known ingestion time no later than declared
availability; assessment cannot precede availability. It reuses the existing causal
feature builder to verify feature values and lineage against the provided snapshots.
No missing history is silently reconstructed. Callers must supply the history needed
for their original features and the immediately preceding record for `gap_seconds`.
This validates submitted evidence, not completeness of a caller's historical archive.

The versioned `EnvironmentalAnomalyContext` retains that entire input, assessment
time, model/version/schema/artifact/manifest identity, score, threshold/method,
imputation, abstention reasons, availability, compatibility and fixed research
limitations. Status is `flagged`, `not_flagged`, `abstained`, or `unassessed` (a scored
row with no configured threshold). Flag comparison remains inclusive `>=`.
Missing/incompatible artifacts give explicit abstention, never a normal result or
substitute estimator. Only model version 1.1.0 / feature schema 1.0.0 is supported.
The reviewed loader additionally enforces scikit-learn runtime equality and SHA-256.
Only trusted artifacts may be loaded; hashes do not authenticate an untrusted author.

See [MODEL_A_INTEGRATION_EXAMPLE.json](MODEL_A_INTEGRATION_EXAMPLE.json) for a full
validated artificial fixture, not a NASA measurement or fitted-model result. Its
score and threshold are both 0.5 from a fake estimator, testing equality. Its real
origin declarations exercise real-source handling in a software fixture; they do not
claim that the artificial measurements were collected by NASA. All-zero/all-one
hashes are test placeholders, not artifact identities.

CO2 concentration remains ppm, temperature degC, humidity %, counts/indicators 1,
and gap s. Each metric has value, 30-minute mean, delta, count and missing indicator.
Synthetic partial pressure Pa is never accepted as ppm. This sidecar is separate from
M4.2 raw-MAD `AnomalyFinding` and never influences M2 ranking. No endpoint, UI, clinical
threshold, exposure pairing, research algorithm or safety action was added.

## Verification

Isolated interpreter: `/tmp/careyonda-model-a-python312/bin/python`, Python 3.12.10.
The environment was created separately, populated by copying existing Python 3.12
packages from Omar's environment plus missing pure-Python API packages from the main
backend environment. No packages were downloaded; neither source environment was
modified. scikit-learn 1.9.1, NumPy 2.4.6 and joblib 1.6.0 match the tested pins.
All 49 applicable pinned requirements across the combined includes match installed
versions; `pip check` reports no broken requirements.

From the integration worktree's `backend/`:

```sh
/tmp/careyonda-model-a-python312/bin/python -m pytest tests/unit/test_nasa_environment_anomaly.py tests/unit/test_environmental_anomaly_context.py tests/integration/test_environmental_anomaly_adapter.py -q
/tmp/careyonda-model-a-python312/bin/python -m pytest -q
/tmp/careyonda-model-a-python312/bin/python -m ruff check app tests ../simulator
/tmp/careyonda-model-a-python312/bin/python -m ruff format --check app tests ../simulator
/tmp/careyonda-model-a-python312/bin/python -m mypy
/tmp/careyonda-model-a-python312/bin/python -m pip check
```

Results: **73 focused tests passed; 368 full-suite tests passed, one skipped**.
The skip is the optional local NASA CSV integration test: measurement files were not
copied into this worktree. Existing FastAPI tests required execution outside the
filesystem sandbox's local TestClient limitation, as previously documented for M3.
Ruff lint/format passed; strict mypy passed for 67 source files. `git diff --check`
passed; the index is empty. The optional fitted-artifact smoke test was not run and
no fitted artifact was loaded. Tests include explicit M2/M4.2 output immutability.

## Remaining limits and next authorized milestone

Original NASA observations have no recorded ingestion time in the existing export.
A caller must supply factual availability/ingestion metadata; this service refuses
unknown availability and does not fabricate historical online access. The statistical
model does not establish physiological exposure or causation, and cannot validate a
hypothesis involving unrelated synthetic astronauts. Dataset/artifact redistribution
constraints are unchanged. No NASA measurements, model artifacts, evaluation files or
credentials were copied into this integration worktree.

Next: review the isolated baseline and adapter, then separately authorize a trusted
local-artifact smoke test with explicit evidence-availability provenance. API exposure
and any change to M2 ranking remain outside this phase and require separate design
and authorization.
