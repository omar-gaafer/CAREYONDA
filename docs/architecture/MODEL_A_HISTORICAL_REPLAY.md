# M-A.3 — Historical replay availability

Implemented 2026-11-13 only in the isolated Model A worktree. No model algorithm,
feature value, M2/M3/M4.2 contract, route or frontend change. No staging or commits.

## Contracts and compatibility

New environmental sidecars write schema **1.1.0**. The reader also accepts existing
1.0.0 live sidecars, including the Phase 1 example. Older consumers must explicitly
support 1.1.0 before accepting new output; forward compatibility is not claimed.
Replay cannot be encoded under 1.0.0. Missing mode fields in legacy inputs mean live,
so they do not relax any previous availability requirement.

`EnvironmentalSample` now declares `assessment_mode` (`live` or
`historical_replay`), `historical_source_availability`, `replay_acquired_at`, and a
`ReplayAcquisition` receipt. Original mission time remains `event_time_utc` and the
original observations retain their original event/ingestion/provenance fields.
The receipt contains record ID, dataset ID, dataset manifest SHA-256, actual local
acquisition time and source reference. Dataset identity and receipt/sample times
must agree. The supplied source reference is declarative, never executed or fetched.

- **Live:** known source availability, non-null `available_at`, and factual non-null
  observation ingestion times no later than that availability. Replay metadata is
  forbidden. Evidence must be available by assessment; previous rejection remains.
- **Historical replay:** `available_at` stays null because source availability is
  unknown; all original source `ingested_at` values must remain null. Actual replay
  acquisition and a matching dataset receipt are mandatory. Acquisition must follow
  source events and be no later than assessment. No event time, file mtime, model
  creation time or service-generated current time substitutes for ingestion.

Sidecars explicitly retain mode, source event time, historical availability, replay
acquisition time, and availability scope (`source_stream` or `careyonda_replay`).
Replay limitations are mandatory and cannot be removed or relabelled as live. A
batch cannot mix modes. Receipt provenance remains a caller declaration; validators
check consistency, not clock authenticity or complete historical acquisition logs.
The service has no clock call or receipt-file I/O. It does not modify observations.

Scoring still uses the existing 16 ordered features, canonical units, transformation,
train-fitted preprocessing and unchanged detector. Threshold comparison stays `>=`;
missing-data and model-unavailable abstentions preserve replay policy metadata.
CO2 ppm is never substituted for synthetic partial pressure Pa. Replay is historical
statistical research, not contemporary human exposure or a causal/clinical finding.

## Changed implementation files

- `backend/app/schemas/environmental_anomaly_context.py`: replay receipt/policy and
  sidecar 1.1.0 validation; legacy 1.0.0 live parsing.
- `backend/app/application/environmental_anomaly.py`: select the explicitly declared
  effective availability; propagate replay policy and mandatory limitations.
- `backend/tests/integration/test_environmental_anomaly_adapter.py`: existing live
  test explicitly narrows nullable availability before its timezone operation.
- `backend/tests/integration/test_environmental_replay.py`: 22 artificial policy and
  regression cases; no NASA values or real acquisition claims in fixtures.
- `backend/tests/integration/test_model_a_replay_local.py`: opt-in trusted local
  acquisition/smoke caller; default suite skips it.
- This report.

## Local real-model verification

The optional smoke caller completed verified reads of the local validated dataset,
recorded their actual completion time in an ignored local receipt, loaded the trusted
Omar artifact, then assessed three original test samples. This establishes only the
new CAREYONDA local replay acquisition, not NASA's historical ingestion. Original
observations remained null for ingestion. Scores/evaluation outputs and measurement
copies were not written into the worktree; only receipt metadata was persisted under
ignored `artifacts/replay_receipts/`. No raw, processed or trained artifact was changed.

To run intentionally, from `backend/` (creates a NEW actual local receipt each run):

```sh
CAREYONDA_MODEL_A_REPLAY_SMOKE=1 \
CAREYONDA_NASA_DATASET=/home/darknight90/CAREYONDA/datasets/processed/nasa_rr1_eda_d2d3_validated \
CAREYONDA_MODEL_A_ARTIFACT=/home/darknight90/CAREYONDA-Omar/artifacts/model_a/nasa_rr1_iforest_v1.1.0_rs42 \
PYTHONDONTWRITEBYTECODE=1 /tmp/careyonda-model-a-python312/bin/python -m pytest tests/integration/test_model_a_replay_local.py -q -s
```

This caller is optional test code, not a new data-ingestion API or permission to
redistribute datasets/artifacts. It does not train anything. Only use the artifact
explicitly trusted by the user; matching hashes alone do not authenticate authorship.

## Results and limits

Python 3.12.10; unchanged scikit-learn 1.9.1, NumPy 2.4.6, joblib 1.6.0 environment.
Focused Model A/adapter/replay suite: **95 passed**. Opt-in trusted replay smoke:
**1 passed**, three samples scored. Full backend: **390 passed, 2 skipped** (opt-in
smoke and original local-NASA fixture test). Ruff lint and formatting passed across
69 files; strict mypy passed for 69 source files; `pip check` and whitespace checks
passed. No dependency changes. Existing M2/M4.2 immutability tests remain passing.

The historical NASA source availability remains unknown. No source timestamp was
backfilled. Acquisition logs are local receipt attestations, not signed evidence.
Live use still needs actual source ingestion/availability provenance and supported
NASA-RR1/ISS context. Replaying an archive does not make it contemporary astronaut
exposure evidence. No API, fusion, diagnosis, safety decision or ranking was added.
