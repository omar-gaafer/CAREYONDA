# M-A.5 — Model A frontend integration

Implemented only in `/tmp/CAREYONDA-model-a-integration`, local branch
`feature/model-a-integration`. Nothing staged, committed, merged or pushed.

## Snapshot and location

The integration worktree lacked the current frontend. Forty-five original source,
configuration and frontend documentation files were copied without touching the
original. [MODEL_A_FRONTEND_SNAPSHOT.json](MODEL_A_FRONTEND_SNAPSHOT.json) records their
hashes. This is an explicitly uncommitted snapshot. Existing local node dependencies
were copied for offline verification; no package was installed or dependency changed.

A compact independent Model A panel appears on `/environment`, above the existing
synthetic environment charts. Crew filters and M2 investigations do not change its
results. The original global fixture/API selector controls its mode, and the existing
`VITE_API_URL` configuration supplies its loopback API origin.

## Changed files

Relative to the copied frontend snapshot:

- `frontend/src/app/{App,ConnectedWorkspace}.tsx`: pass mode and existing API URL.
- `frontend/src/features/environment/Environment.tsx`: mount the independent panel;
  clarify that charts remain synthetic and Model A context is separate.
- `frontend/src/styles.css`: scoped responsive provenance layout/word wrapping.

New frontend implementation/test files:

- `frontend/src/contracts/model-a.ts`: strict Zod API/sidecar v1.1.0 validation,
  source/timing/units/lineage/flag consistency.
- `frontend/src/infrastructure/model-a.ts`: dedicated no-fallback HTTP client.
- `frontend/src/infrastructure/fixtures/model-a-simulated.json`: artificial software
  fixture generated with a fake estimator; no NASA measurements or trained artifact.
- `frontend/src/features/model-a/ModelAPanel.tsx`: selection, requests and rendering.
- `frontend/src/features/model-a/model-a.test.tsx`: 25 focused client/schema/UI cases.
- `frontend/src/features/model-a/model-a.local.test.tsx`: opt-in actual HTTP-to-React-DOM
  smoke; skipped by default and excluded from production bundles.

Minimal backend extension (documented and tested):

- `backend/app/application/environmental_api.py`: safe catalog listing and lookup.
- `backend/app/api/environmental_anomaly.py`: metadata-only authorized-reference GET
  and backward-compatible schema 1.1.0 reference POST; old full-sample requests remain.
- `backend/tests/integration/test_model_a_api.py`: discovery, reference assessment,
  forged/extra-field rejection, no filesystem metadata in discovery.

Documentation: this report, snapshot manifest, and the M-A.5 extension section in
[MODEL_A_ENVIRONMENTAL_API_V1.md](../api/MODEL_A_ENVIRONMENTAL_API_V1.md).
M2/M4.2, model scoring/thresholds, feature values, M3 routes and frontend dependencies
are unchanged.

## Connectivity and trust

The browser discovers server-authorized references and submits only sample ID, mode
and its explicit requested assessment time. It never creates acquisition receipts,
chooses artifact paths, sends filesystem paths or asserts server authorization.
Server resolution uses the same independently provisioned catalog and verified receipt
registry as M-A.4. No catalog entry or model means an explicit unavailable state.
The GET contains reference metadata, not datasets. The full POST sidecar retains
server provenance; filesystem source references are opaque to the client and are
neither displayed nor dereferenced. The UI displays receipt IDs instead.

The dedicated client checks a credential-free loopback HTTP origin, omits credentials,
uses no-store, forbids redirects, and times requests out after ten seconds. It validates
responses at runtime, IDs/modes/assessment correlation, exact feature units/order,
source context, observation lineage, temporal availability and inclusive flag semantics.
Errors never trigger fixture fallback. API mode uses the new Model A factory; the
unchanged M3-only factory does not provide the added routes.

Fixture mode does not call the network and is explicitly labelled **SIMULATED MODEL A
DEMO**. Its artificial observations use real-source declarations only to exercise the
software contract; they are not NASA measurements. It is a live-shaped artificial
fixture, not a fabricated replay receipt. Its score is from a fake estimator, not
trained-model inference. Mode changes reset session state; selection/refresh invalidates
stale assessments rather than displaying them as a newly selected result.

## Panel states and content

Loading, successful flagged/not_flagged/unassessed, missing-data abstention, model 503,
missing authorized samples, 403 receipt/authorization rejection, 422 invalid input,
backend failure and malformed contract are explicit. The panel preserves correlation
IDs and shows no substitute result after errors. No clinical risk/severity/confidence
visualization was introduced.

The result shows model availability/identity/version, mode, statistical score and
threshold/method, original event time, replay acquisition and assessment time, source
availability (including unknown), availability scope, imputation/abstention reasons,
mission/environment/dataset/run, receipt ID, lineage, source IDs/methods/quality,
artifact/schema/manifest identity, and research-only limitations. Provenance details
are collapsible. NASA ppm and synthetic Pa remain separate.

## Verification

- Frontend: **106 passed, 1 expected optional-smoke skip**, retaining all 81 original
  cases; the 25 new cases cover schema/client/UI behavior.
- Live trusted-model smoke: **1 passed** separately. The rendered panel discovered a
  real local authorized NASA replay reference, submitted only that reference to the
  actual Uvicorn API, validated the response and displayed the actual not_flagged
  replay result and unknown historical source availability. No HTTP response was
  mocked. This was React DOM/jsdom integration, not manual browser visual QA.
- TypeScript, production build and Prettier checks passed. Two existing nonfatal
  upstream Zod Rollup comment-annotation warnings remain.
- Backend: **419 passed, 2 expected skips**, including 29 Model A API cases. Ruff
  lint/format, strict mypy (73 source files), dependency and whitespace checks passed.

The actual smoke server was configured only in ignored local verification code using
Omar's explicitly trusted artifact and the existing factual M-A.3 replay receipt.
Existing NASA data/manifest fingerprints were verified. No new acquisition timestamp
was invented. No NASA measurement or fitted artifact was written into frontend source
or the production bundle. The smoke server was stopped after verification.

The opt-in DOM smoke uses a Node/jsdom AbortSignal transport bridge because Node fetch
and jsdom use distinct signal realms; it does not mock HTTP responses. Production
browser requests retain their timeout. To rerun against an intentionally configured
local research server:

```sh
VITE_MODEL_A_E2E_URL=http://127.0.0.1:8765 npm --prefix frontend test -- src/features/model-a/model-a.local.test.tsx
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run format:check
```

The optional smoke expects the documented verified first RR-1 test result and requires
server-side approved samples/receipt/artifact provisioning. Never point it at an
untrusted artifact or change receipts to obtain a successful request.

## Remaining limits and next milestone

Model A remains unavailable on an unconfigured server. Deployment must provide the
trusted local artifact, actual acquisition receipts and authorized sample catalog;
none are bundled with the browser. Dataset/artifact redistribution constraints remain.
There is no upload/import/receipt-creation UI, persistence, production authentication,
new research method, medical assessment or M2 ranking change. Existing API remains
loopback-only research software. The original global source label continues to describe
synthetic M3 charts/investigations; the Model A panel labels its own source separately.

Next: separately review the isolated backend/frontend snapshots and authorize a
reproducible local demo configuration and browser acceptance check. Do not automatically
publish data, commit, integrate another model or alter hazard reasoning.
