# M3 — local API and frontend integration report

Implemented incrementally on the existing `feature/hazard-reasoning` branch, 2026-11-13. The initial tree contained three modified M2 files (`explanations.py`, `schemas/evidence.py`, `schemas/investigation.py`), four untracked M2 source/test/report files, and the untracked Phase 1/2 frontend. These were preserved. No branch switch, staging, commit, push, raw/processed dataset edit or M2 algorithm/research change occurred.

## Delivered architecture and files

- `backend/app/main.py`: composition factory, explicit disabled framework telemetry, sanitized error handlers and restrictive local middleware. No import-time source loading.
- `backend/app/api/{contracts,routes,security}.py`: versioned transport models/routes, structured errors/correlation IDs, bounded body/query parsing, host/origin restrictions and no-store responses. Existing empty API placeholders were left intact.
- `backend/app/application/{__init__,evidence}.py`: the first concrete application workflow, using an injected read-only source protocol. Its thin adapter invokes the unchanged M2 function with a configured preset's original observations and anchors.
- `backend/app/storage/{local_evidence.py,fixtures/api_evidence.json}`: validated synthetic-only, startup-loaded source. The new fixture contains 145 observations and four context presets copied from existing frontend synthetic evidence, with no precomputed investigation result. Backend runtime does not depend on frontend files or research datasets.
- `backend/pyproject.toml`: FastAPI/Uvicorn runtime declarations, HTTPX development declaration and one exact upstream test-client warning exception. `requirements-m3-resolved.txt` records the tested pinned environment; the older snapshot remains untouched.
- `backend/tests/integration/test_local_api.py`: 20 API integration cases, including exact comparison to the existing engine for four result modes.
- `frontend/src/contracts/api.ts`, `infrastructure/http.ts`, `app/ConnectedWorkspace.tsx`, `src/vite-env.d.ts`, `.env.example`: versioned runtime validation, typed loopback-only HTTP repositories, explicit source composition and build-time API origin configuration.
- Extended frontend app/shell, investigation hook/interface/workspace, source provenance display, synthetic envelope, styling, `.gitignore`, README and thirteen HTTP/mode integration tests. Fixture/API switching deliberately remounts session state and never silently falls back.
- Documentation: root README status/startup links, `docs/api/LOCAL_API_V1.md`, this report, frontend README and `frontend/PHASE3_INTEGRATION.md`. Historical research/architecture reports were not rewritten.

The API implements health, capabilities, contexts, paginated observation collection/detail and POST investigation under `/api/v1`. It does not implement authentication, NASA data loading, uploads, persistent result retrieval, incident persistence, trained models or approved medical/safety workflows. Availability is explicitly separate from medical validation.

## Verification results

| Check                                                       | Result                                                                 |
| ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| Existing backend regression suite before API test additions | 192 passed                                                             |
| Final full backend pytest                                   | **212 passed**, including 20 new API cases                             |
| Backend Ruff lint                                           | Passed using existing configuration from `backend/`                    |
| Backend Ruff formatting                                     | Passed, 53 files checked                                               |
| Backend strict mypy                                         | Passed, 53 source files                                                |
| Existing Phase 1/2 frontend regression suite                | All original 68 cases retained and passing                             |
| Final frontend suite                                        | **81 passed**, six files                                               |
| Frontend strict TypeScript                                  | Passed                                                                 |
| Frontend Prettier check                                     | Passed                                                                 |
| Frontend production build                                   | Passed; existing two non-fatal third-party Zod comment warnings remain |
| Git diff whitespace check                                   | Passed                                                                 |
| Real local Chrome API integration                           | Passed, as detailed below                                              |

API tests cover health/capability distinctions, bounds, configured contexts, metric/subject/time filters, pagination, provenance equality, invalid identifiers, timezone-naive/ordered windows, malformed/unsupported request versions, injected fields, all M2 selection/abstention modes, preserved safety, unknown retrieval, exact and excessive body boundaries (including missing Content-Length), JSON media type, query size, hosts/origins, sanitized internal failures and telemetry disabled despite an enabling environment variable.

Frontend integration tests cover fixture mode without HTTP calls, explicit API switch, paged success, request contracts, observation provenance, shared crew filtering, actual result envelope mapping, safety/abstention UI, newly submitted result selection, non-local/credentialed URL rejection, unavailable/malformed/unsupported responses, pagination truncation and no silent fallback. Earlier regression tests still cover all twelve routes, incident session workflows, keyboard navigation, evidence links, offline state and observation validation.

## Executed browser demonstration

Started Uvicorn at `127.0.0.1:8000` with access logging off and the built frontend preview at `127.0.0.1:4173`. Installed Chrome 156 loaded the real application in a same-origin QA frame and:

1. Selected **Local API · synthetic**, triggering real observation/context GET requests.
2. Submitted a configured investigation through POST; observed `PATTERN SELECTED`, `not_evaluated`, 18 current/18 reference IDs and `computed by local M2 API` provenance.
3. Clicked an evidence reference and confirmed the original `simulated / phase2-fixture` observation provenance in the detail panel.
4. Changed to crew-02, submitted its configured windows and observed **ABSTAINED**, unchanged safety and API origin.
5. Verified the connected document had equal scroll/client widths at desktop size (1425px).
6. Stopped the backend, opened Data Explorer in a narrow frame and selected API mode. Confirmed mode remained `api`, an explicit source/validation error appeared, no observation table was substituted, and scroll/client widths matched at 390px.

Local ignored QA logs under `frontend/.qa/` record the browser outcomes. Temporary browser harness files are excluded from source and removed from final `dist/` by rebuilding. Both owned servers were stopped after verification. This is real local transport smoke coverage, not merely a mocked fetch test, and not complete browser accessibility/performance certification.

## Tooling exceptions and resolved failures

The sandbox could not resolve PyPI, so authorized dependency installation completed outside that sandbox. Package versions and a reproducibility strategy were declared before installation, then pinned in the M3 snapshot. FastAPI's installed telemetry support was inspected and explicitly disabled for this research application; no exporter or external runtime service is used.

Starlette's TestClient hung while starting its AnyIO thread portal inside the execution sandbox. A diagnostic confirmed the wait, the hung run was interrupted, and the identical full suite completed outside that sandbox in roughly three seconds. Tests themselves are deterministic and offline. Starlette 1.10's exact HTTPX transition deprecation is narrowly documented in `pyproject.toml`; all other warnings remain errors. No broad mypy or lint bypass was added.

Initial integration checks caught duplicated correlation response headers, a test-only observation-count assumption, inferred JSON union typing, and selection of an older result after a new submission. These were corrected; final checks pass. There is no configured frontend ESLint command, so no ESLint pass is claimed. Production build still reports the existing harmless Zod annotation warnings. No required final check remains blocked.

## Limits and next task

The source is synthetic-only and publicly readable to permitted local clients; context allowlisting is not user authentication. Never expose it or load real health/mission records without a separate identity, authorization, retention and deployment milestone. CORS/host checks are defense-in-depth, not a multi-user security boundary. No operational or medical suitability is established.

API snapshots contain multiple controlled synthetic cases; they are not paired NASA/human data or one continuous mission series. API-mode views preserve their original provenance, missingness, event times and incompatible units without conversion. The frontend still supports a reviewed subset of backend metrics. M2's reference/ranking limitations and `safety_status=not_evaluated` remain unchanged.

HTTP operations have ten-second frontend timeouts; loaded evidence is an in-memory snapshot, not a live subscription. Errors on new requests are explicit. A previous successful result may remain visible after a failed submission only with an explicit failure notice. Switching mode or reloading clears workflow notes/results; no persistence is claimed. The service has no public-deployment hardening or user identity and is intentionally loopback-only.

Next task: review the local connected workflow. Any measured-data source, persistence, authentication or operational rule requires a separately approved contract and implementation milestone. Startup and exact endpoint contracts are in [LOCAL_API_V1.md](LOCAL_API_V1.md); frontend steps and mapping are in [PHASE3_INTEGRATION.md](../../frontend/PHASE3_INTEGRATION.md).
