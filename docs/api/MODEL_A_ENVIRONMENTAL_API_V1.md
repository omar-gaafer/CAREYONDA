# M-A.4 — Optional Model A environmental API

Implemented in the isolated `feature/model-a-integration` worktree, 2026-11-13.
All changes are additions. Existing M3 composition, routes/security/contracts, M2,
M4.2, frontend, detector, thresholds and research sidecar contracts are unchanged.

## Endpoint and HTTP contract

`POST /api/v1/environmental/anomaly-context` is available through the new optional
composition root `app.model_a_main:create_app`. It wraps the existing M3 application
and adds one router; the original `app.main:create_app` remains unchanged.

Request: `schema_version: "1.0.0"`, explicit timezone-aware `assessed_at`, and `samples`
containing one or two complete validated `EnvironmentalSample` records. Each includes
original observations, feature values/units/lineage, scope and availability metadata.
Replay additionally requires the M-A.3 acquisition receipt and unknown/null original
source availability. HTTP has no artifact path, receipt-upload, source-registration or
clock-override field. Extra fields are forbidden.

200 response: `api_version: "1.0.0"`, server-generated `correlation_id`,
`model_availability: "available"`, `contexts` containing sidecar v1.1.0 results, and
explicit research `limitations`. Score/threshold, imputation, provenance, assessment
mode, availability scope and flag/abstention remain inside each complete sidecar.
`unassessed` remains possible when the injected detector has no configured threshold.
Flags use the existing inclusive `>=` decision. These are not diagnoses or exposure
attributions.

503 response uses the same response contract with availability `unavailable` or
`incompatible`, empty contexts, and an explicit no-inference/no-fallback limitation.
No submitted provenance is accepted by this response. Model availability is checked
after request schema validation, before evidence authorization/scoring.
403 rejects provenance absent from or differing from the server catalog.
422 rejects malformed inputs, future assessment, future-unavailable evidence or
invalid assessment windows. 413 rejects oversized bodies. Unexpected failures become
sanitized 500 errors through the existing request guard. All error responses use the
existing error envelope with a correlation ID; local paths and exception text are not
reflected. `X-Correlation-ID` matches response IDs and is always server-owned.

## Server-only trust and configuration

The endpoint never promotes an HTTP availability/ingestion/receipt declaration to
trusted provenance. An operator supplies `ModelAConfig.authorized_samples` from an
independently trusted acquisition workflow. Complete client samples must exactly
match those server-side immutable snapshots, including measurements, source IDs,
ingestion/availability, feature lineage and replay metadata. The service receives
the server snapshot rather than the client object.

For replay, the operator also configures `replay_receipt_files`. Startup reads and
validates those local receipts, and each authorized replay sample's full receipt must
match a registered record. Dataset ID, manifest hash, receipt ID, timestamp and source
reference are retained. Client-provided source references never trigger file access.
A filesystem receipt is an operator-trusted local attestation, not a cryptographic
proof of historical NASA availability. Unknown source ingestion remains null. No HTTP
endpoint creates receipts, backfills ingestion or registers evidence. Catalog
provisioning must not be fed from unverified request bodies.

Server configuration is Python deployment composition, for example:

```python
from pathlib import Path
from app.model_a_main import ModelAConfig, create_app

# Provision these snapshots/receipt files through the approved local acquisition
# workflow; they are not accepted from an HTTP caller.
config = ModelAConfig(
    artifact_directory=Path(TRUSTED_LOCAL_MODEL_DIRECTORY),
    authorized_samples=AUTHORIZED_ENVIRONMENTAL_SAMPLES,
    replay_receipt_files=APPROVED_LOCAL_RECEIPT_FILES,
)
app = create_app(config)
```

An unconfigured but healthy extension can be started from `backend/` with:

```sh
/tmp/careyonda-model-a-python312/bin/python -m uvicorn app.model_a_main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

It returns model-unavailable responses until deliberately configured. Existing M3
capabilities/health/context/observation endpoints retain their original synthetic-only
meaning; the new response's `model_availability` describes this separate extension.
No discovery endpoint for authorized NASA samples was added.

## Lifecycle and bounds

Dependencies are injected: server config, loader, clock, application gateway and
existing inference service. Lifespan loads receipts/model once before serving and
clears the binding/catalog at shutdown. No per-request model load occurs. Optional
ML imports happen only for explicit configured local model files. Startup without
Model A packages is tested and remains healthy. Missing files/packages give
unavailable state; incompatible metadata/runtime/artifact gives incompatible state.
Broken server receipt/catalog configuration fails closed and leaves existing health
and M3 routes operational. No synthetic model is substituted.

Artifact loading uses the existing trusted Model A loader with SHA-256, supported
model/schema checks and exact scikit-learn compatibility. Only load artifacts trusted
through the team's existing local workflow; hashes alone do not authenticate origin.
Startup bounds: 128 authorized samples, 128 observations per sample, 32 receipts,
16 KiB per receipt, 256 KiB metadata and 64 MiB joblib. These bound ordinary local
initialization; no hard wall-clock deadline or sandbox for trusted pickle loading is
introduced. Request batch maximum is two. The unchanged global guard limits every
body to 16,384 bytes (also checked while receiving chunks), query to 2,048 bytes, JSON
POST content, allowed loopback hosts/origins, and no-store responses. Long evidence
histories can exceed this body limit even for one sample; they are rejected rather
than truncated. Bind to loopback as before; Host/Origin checks are not authentication.

The API requires an explicit assessment timestamp no later than its server clock.
The inference adapter still enforces acquisition/availability <= assessment. The API
clock is not used to invent source ingestion, replay acquisition or assessment times.

## Files and verification

Added files only:

- `backend/app/api/environmental_anomaly.py`: Pydantic v2 HTTP models/router.
- `backend/app/application/environmental_api.py`: inference protocol/binding and
  exact server-authorized provenance boundary.
- `backend/app/model_a_main.py`: optional composition/lifespan and server-only loading.
- `backend/tests/integration/test_model_a_api.py`: 27 artificial/fake-estimator cases.
- This report.

Python 3.12.10, existing dependencies unchanged. Results:

- Model A API: **27 passed**.
- Full backend: **417 passed, 2 expected skips** (optional real replay smoke and local
  NASA CSV test). The optional real artifact was not loaded for this milestone.
- Ruff lint and formatting passed; strict mypy passed for 73 source files.
- `pip check` and Git/new-file whitespace checks passed.
- Original 71 dirty-file hashes and Git status unchanged; all pre-existing integration
  files unchanged; no staging, commits, pushes or data/artifact copies.

The tests cover healthy optional startup with ML imports blocked, configured model,
live/replay success, missing/forged/invalid receipts, future times, imputation/abstention,
feature order/units, synthetic-origin rejection, two-sample boundary, body limit,
correlation IDs, sanitized errors, one-time loading and M2/M4.2 preservation.

## Frontend work remaining

Separately authorize a client for the new request/response and sidecar v1.1.0 shapes.
Provision approved sample snapshots and server receipts through an explicit local
workflow; this endpoint is not a dataset upload/import API. Render unavailable and
abstained states, research limitations, original event versus replay/assessment times,
provenance and correlation IDs. Keep real NASA replay context separate from synthetic
M2 investigation rankings and never present it as contemporary astronaut exposure.
No frontend code was changed.

## M-A.5 — Backward-compatible browser reference extension

To avoid sending filesystem paths or complete acquisition records from browsers,
`GET /api/v1/environmental/authorized-samples` now returns API v1.0.0 metadata:
`correlation_id`, `model_availability`, and `samples`. Each summary contains only
`sample_id`, `assessment_mode`, `source_event_time`, mission/environment/dataset/run
`scope`, and nullable `receipt_id`. It contains no feature measurements, observations,
artifact paths or receipt source references. Unconfigured servers return an empty
list and unavailable state. No sample or receipt is created by discovery.

The existing POST additionally accepts **request schema 1.1.0**:

```json
{
  "schema_version": "1.1.0",
  "assessed_at": "2026-11-13T21:00:00Z",
  "sample_references": [
    {"sample_id": "server-issued-id", "assessment_mode": "historical_replay"}
  ]
}
```

The timestamp is a requested assessment time, not acquisition/ingestion evidence.
The server resolves references only from its existing authorized catalog and applies
all existing receipt, availability and inference checks. Unknown references return
403. Extra reference fields, fabricated receipt declarations and mixed request
shapes are rejected. Batch maximum remains two. The original request schema 1.0.0
with full `samples` remains unchanged and tested. Response API v1.0.0 and research
sidecar v1.1.0 remain unchanged. Receipts are never accepted or trusted from this new
HTTP request. This is a documented extension, not a change to the receipt trust policy.
