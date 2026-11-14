# CAREYONDA local API v1 — M3

This is a loopback-only, unauthenticated research API with a configured **synthetic-only** catalog. It is not a medical service, a multi-user authorization system, or a public deployment. All clinical validation flags are false. M2 runs deterministically on submitted configured contexts; its research algorithms are unchanged.

## Provision and start

Python source targets 3.11+; this milestone was tested on Python 3.14.8. Runtime declarations are in `backend/pyproject.toml`; `backend/requirements-m3-resolved.txt` pins the tested runtime and development environment, including FastAPI 0.162.7, Starlette 1.10.0, Uvicorn 0.54.0 and HTTPX 0.28.1. Preserve the earlier M1 snapshot. The M3 snapshot is a tested pip freeze, not a cross-platform hashed lock. Provision compatible wheels separately for disconnected installation.

From repository root, with the existing virtual environment (or a separately prepared environment):

```sh
backend/.venv/bin/python -m pip install -r backend/requirements-m3-resolved.txt
cd backend
.venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Installation requires registry access or a complete local wheel/cache bundle. Runtime requires no internet, cloud service, model download, credential or raw dataset. Do not use `--host 0.0.0.0`. No authentication has been implemented; host/origin checks and configured-context restrictions do not authenticate users or protect a shared workstation. Do not provision real health records or expose the process through a tunnel/proxy/public listener.

The factory loads only `backend/app/storage/fixtures/api_evidence.json`. No import-time I/O occurs. An operator can inject an `EvidenceSource` into the factory for tests, but this API version rejects non-simulated origins. No request accepts a filesystem path, uploaded observations, external URL, or executable configuration. The catalog is an independent versioned synthetic evidence artifact copied from the Phase 2 observations/anchors; it contains no precomputed result and has no runtime frontend dependency. Its 145 observations represent four controlled cases, including contradictory cases for the same fictional crew/time. They are not a continuous real mission history. M2 receives only the selected preset's collection, never an aggregate across those cases.

## Endpoints

All JSON envelopes use `api_version="1.0.0"`; data envelopes use `source="configured_synthetic"`. Observation detail returns the original domain `Observation` directly with `schema_version="1.0.0"`. These versions are different namespaces even though their current values match. `/openapi.json` provides the local machine-readable specification; Swagger/ReDoc UI is disabled to avoid remote CDN assets.

| Method/path                                 | Request                                                 | Response                                                                                        |
| ------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `GET /api/v1/health`                        | None                                                    | Version, `status=ok`, configured synthetic source                                               |
| `GET /api/v1/capabilities`                  | None                                                    | Capability availability and explicit medical-validation false; authentication `none_local_only` |
| `GET /api/v1/contexts`                      | None                                                    | Allowed presets: title, complete current and reference `SampleAnchor`                           |
| `GET /api/v1/observations`                  | Optional filters below                                  | Version/source, original `items`, `total`, `limit`, `offset`                                    |
| `GET /api/v1/observations/{observation_id}` | Existing canonical identifier                           | Original validated observation, including source quality and provenance                         |
| `POST /api/v1/investigations`               | Version, exact current/reference anchors, window length | Version/source envelope and unchanged M2 `result`                                               |

Capabilities distinguish `available` (contract validation), `simulation_only` (observation delivery and M2 reasoning), and `not_implemented` (safety policies, trained models and investigation persistence). Every entry has `medically_validated=false`. A health response only means the local service can answer; it does not establish subject/spacecraft health or operational readiness.

Observation query parameters:

- `mission_id`, `astronaut_id`, `metric`: canonical identifiers (1–128 characters). Mission and subject values must be configured or receive 403. Unknown metrics receive 422. The full backend registry defines accepted metric names, but a known metric may have zero configured records.
- `start`, `end`: timezone-aware event timestamps, inclusive bounds; start must not exceed end. Sampling intervals are preserved. Ingestion time is never substituted for event time.
- `limit`: integer 1–100, default 100. `offset`: integer 0–10000, default 0. Beyond-end pages are empty. Ordering is `(event time, observation ID)`.
- Subject filtering selects astronaut-scoped records only; it does not imply environmental pairing. Omit the subject filter to inspect habitat evidence. The frontend obtains bounded catalog pages and applies its existing display filters locally.

The API preserves raw measurement variants, missingness, canonical units, scope, provenance and source quality. No NASA records are loaded in this version. NASA/environmental evidence must remain separately provisioned and semantically separate in any future source milestone. No ppm/Pa conversion or NASA-to-human pairing occurs.

## Investigation request and response

Retrieve configured anchors from `/contexts`, then submit their exact values:

```json
{
  "schema_version": "1.0.0",
  "current": {
    "sample_id": "ranked-current",
    "episode_id": "ranked-episode",
    "mission_id": "ARES-07",
    "astronaut_id": "crew-01",
    "spacecraft_id": "HABITAT-01",
    "compartment_id": "LAB-01",
    "timestamp": "2026-11-13T11:55:00Z"
  },
  "reference": {
    "sample_id": "ranked-reference",
    "episode_id": "ranked-episode",
    "mission_id": "ARES-07",
    "astronaut_id": "crew-01",
    "spacecraft_id": "HABITAT-01",
    "compartment_id": "LAB-01",
    "timestamp": "2026-11-13T11:40:00Z"
  },
  "window_seconds": 300
}
```

A runnable local example:

```python
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False) as client:
    preset = client.get("/api/v1/contexts").json()["presets"][0]
    response = client.post("/api/v1/investigations", json={
        "schema_version": "1.0.0",
        "current": preset["current"],
        "reference": preset["reference"],
        "window_seconds": 300,
    })
    response.raise_for_status()
    result = response.json()["result"]
    assert result["safety_status"] == "not_evaluated"
```

Only exact paired configured anchors are accepted; changing mission, astronaut, location, sample, episode or endpoint returns 403. Window length is a strict positive integer at most 3600 seconds. M2 additionally requires reference end no later than the exclusive start of the current window; overlap returns 422. Data is selected by M2's existing `(anchor-window, anchor]` event-time and exact scope rules. The reference is an empirical comparator, not assumed healthy. Retrospective availability semantics remain unchanged.

`result` is the original `Investigation` contract: `schema_version=1.0.0`, `engine_version=reference-rules-1.0.0`, ranks/ties/order, selection or abstention, all evidence groups/IDs, explanations, uncertainty, quality issues and `safety_status=not_evaluated`. No probability, confidence percentage, diagnosis, recommendation or treatment is added. Every request recomputes the result. There is no persistent retrieval endpoint or database.

## Errors, bounds and local trust boundary

Errors have only version, safe code, and a server-generated correlation ID:

```json
{
  "api_version": "1.0.0",
  "error": {
    "code": "invalid_request",
    "correlation_id": "server-generated-hex-id"
  }
}
```

The same ID appears once in `X-Correlation-ID`. Request validation and HTTP exception details are not reflected. Bodies, measurements, source exceptions and request-provided correlation headers are not logged or returned. Responses use `Cache-Control: no-store`; application responses also use `X-Content-Type-Options: nosniff`. Successful responses and errors have correlation IDs. The startup command disables access logs, which could otherwise contain query identifiers.

- Body cap: **16384 bytes**, checked using both declared Content-Length and counted ASGI chunks before JSON parsing, including requests without Content-Length. Exact boundary is allowed; over-boundary requests return 413.
- Query-string cap: 2048 bytes; larger requests return 414.
- POST requires `application/json` (415 otherwise); malformed JSON/contracts/versions use 422. Unconfigured context uses 403; unknown evidence uses 404; internal exceptions use sanitized 500.
- Hosts: IPv4 loopback `127.0.0.1` and `localhost`. This version does not configure IPv6 listening.
- Origins: only `http://127.0.0.1:5173`, `http://localhost:5173`, and the same hosts on 4173. GET/POST only, Content-Type allowed, credentials disabled. Unexpected Origin is rejected before handling. CORS does not authenticate a user or block non-browser local clients.
- FastAPI tracing, metrics, logs, operation spans and automatic exporter configuration are explicitly disabled, including when `FASTAPI_OTEL_AUTO_CONFIGURE=true`. OpenTelemetry API is a framework transitive package; no exporter/SDK is configured or required.

Foundation implementation references: [FastAPI exception handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/) and [explicit CORS configuration](https://fastapi.tiangolo.com/tutorial/cors/).

## Quality checks

From `backend`:

```sh
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

Starlette 1.10 retains HTTPX test-client compatibility but emits a deprecation warning for its transition to `httpx2`. `pyproject.toml` contains one exact-message/category exception for that upstream compatibility warning; all other warnings remain errors. No broad warning suppression, mypy exclusion or missing-import suppression is used. In the restricted execution environment the TestClient thread portal hangs; the same offline suite passes outside that sandbox. This is an execution-environment limitation, not a need for network access in tests.
