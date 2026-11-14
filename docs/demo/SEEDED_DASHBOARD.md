# Local PostgreSQL synthetic research dashboard

Status: **working local database-to-API-to-browser viewer**, not a public deployment,
Supabase activation, authenticated patient workflow or AI inference integration.
Branch `feature/seeded-dashboard`, base
`fcea4af2ab6c9c065ae5da5747d64c1acf9eb5cd`. Reviewed source checkpoint;
local database and dependency environments are excluded.

## Data and source preservation

Uses the already populated `careyonda_demo_seed_local` database, socket
`/tmp/careyonda-seeding-socket`, port 55438. No data was generated, inserted,
updated or deleted by viewer setup. The seed implementation and tests/documentation
were copied selectively from protected `CAREYONDA-demo-seeding`; they are not run
to populate another database. Unit tests may construct ephemeral synthetic
fixtures, but do not store data. Existing worktrees remain unchanged.

Exact seed-field SHA-256 before and after setup/acceptance:
`7e7cc664f88dff71b8a51110a30dbf529206c7dafd939a9d09a62dfa4fbd93d1`.

Actual SELECT results:

| Table | Approved rows |
| --- | ---: |
| missions | 2 |
| spacecraft | 2 |
| compartments | 2 |
| astronaut_profiles | 6 |
| observations | 1,332 |
| numeric_measurements | 803 |
| boolean_measurements | 215 |
| categorical_measurements | 210 |
| unavailable_measurements | 104 |
| observation_quality_reasons | 176 |
| **Total** | **2,852** |

Each mission has 666 observations. The six astronaut IDs are fictional and have
null user identity mappings. Scope associations displayed in the catalog are
queried from observations, not invented mission/doctor assignment records.
All observations remain simulated with seed/run/version/scenario/source lineage.
CO2 is synthetic partial pressure in Pa, not NASA concentration in ppm. Historical
NASA and model artifacts are not loaded, copied, bundled or exposed by this viewer.

## Dedicated identity and RLS

Provisioning uses `backend/scripts/configure_synthetic_reader.py`, explicitly
restricted to this named disposable local socket database. It verifies all 2,852
existing seed fields against the recorded SHA-256 before changing permissions.
It does not generate fixtures or create Auth users.

- Reader: `careyonda_synthetic_viewer`, LOGIN, NOINHERIT, NOSUPERUSER,
  NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; no role memberships or
  application-table ownership.
- SELECT only on the ten approved tables; no application-table write grants.
  Role default is read-only and every application query explicitly runs in a
  read-only transaction with row security enabled.
- Ten SELECT policies apply only to that role. Observation access is pinned to the
  exact 1,332 approved UUIDs plus simulated origin/source/run/version/seed/mission
  requirements. Measurement/quality policies depend on RLS-visible observations.
  Mission/ship/profile policies allow only the fictional identifiers; astronaut
  `user_id` must remain null.
- All 35 tables retain RLS. No PUBLIC, authenticated or preexisting-reader policy
  is added. The preexisting `careyonda_seed_reader` still sees zero observations.
  Profiles, Auth users, private records and unrelated tables are not granted.
- Runtime rejects owner/privileged/writable identities and checks 35 RLS flags and
  the exact reviewed policy SHA-256:
  `08ef9c893eed94b9a2b228dbb5f359418c8a5cda5ef3250704c5bdec914bf542`.
  Policy drift or extra policies fail closed. A future policy/schema change needs
  explicit review, not a bypass or automatic pin update.
- The local PostgreSQL instance has no network listener. Its socket directory is
  owner-only (0700). Existing local trust authentication is limited by that OS
  boundary; no password or service-role key is sent to a browser.

Initial migration verification expected zero client policies. This optional local
viewer intentionally adds ten role-specific policies afterward; do not weaken
RLS or change the initial verifier to pretend this is still the zero-policy state.
The copied seed runner also deliberately rejects policy-bearing targets, so do
not rerun seeding against this viewer-enabled database.

Already provisioned here. For an equivalently verified existing local seed only:

```sh
cd "$HOME/CAREYONDA-seeded-dashboard/backend"
export PYTHON="$HOME/CAREYONDA-model-b-python312/bin/python"
PYTHONPATH=.:.. "$PYTHON" -m scripts.configure_synthetic_reader \
  --database 'host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local' \
  --confirm-approved-synthetic
```

The setup command uses the authorized local database owner only for reviewed role
and policy administration. The running API never uses that identity. No privileged
fallback exists. The same-project Supabase configuration hold remains untouched.

## Enable and run

Backend is **disabled by default**. Only the explicit local factory knows these
routes; normal `app.main` and `app.final_main` return 404 for them even if the
viewer environment flag is set. No public/Replit factory was modified.

```sh
cd "$HOME/CAREYONDA-seeded-dashboard/backend"
export PYTHON="$HOME/CAREYONDA-model-b-python312/bin/python"
export PYTHONPATH=/tmp/careyonda-remediation-deps
export PYTHONDONTWRITEBYTECODE=1
export CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER=1
export CAREYONDA_SYNTHETIC_DB_URL='host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local user=careyonda_synthetic_viewer'
"$PYTHON" -m uvicorn app.seeded_main:create_app --factory \
  --host 127.0.0.1 --port 8110 --no-proxy-headers
```

Use existing provisioned frontend dependencies, then:

```sh
cd "$HOME/CAREYONDA-seeded-dashboard/frontend"
VITE_LOCAL_SYNTHETIC_VIEWER=true VITE_API_URL=http://127.0.0.1:8110 npm run build
npm run preview -- --host 127.0.0.1 --port 5181 --strictPort
```

Open **http://127.0.0.1:5181/synthetic-database**. The latest shell adds the
**Local Synthetic Data** navigation item only in this opt-in build. Required
labels are visible: **Synthetic Research Dataset**, **Local PostgreSQL**,
**Not Live Astronaut Telemetry**.

The page displays queried mission/ship/fictional profile IDs, numeric/categorical/
boolean/missing observations, separate UTC event/ingestion times, units, quality,
source and scenario provenance. Mission, simulator-source and metric filters
query the database. Charts require one simulator source and one numeric metric;
subjects/streams are not silently fused. Chart and table use only the current
bounded page. Missing/suspect samples produce gaps, never normal/zero values.
Wide evidence tables scroll within their container. The chart-evidence link stays
on this local database page.

Blank source/metric selections browse all 666 mission observations across seven
pages, maximum 100 per request. This is not a claim that 2,852 observations exist:
2,852 includes relational measurement/provenance/entity rows.

## API and isolation

- `GET /api/v1/local-synthetic/catalog`
- `GET /api/v1/local-synthetic/observations?mission_id=...&limit=100&offset=0`
- Optional observation query filters: `metric`, `source_id`.

Responses use version 1.0.0 and explicit source `synthetic_database`. Pydantic
response models and fixed SQL projections allowlist fields. No SQL, table name,
artifact path, database URL or credential is accepted from HTTP callers.
Mission IDs are allowlisted, limits 1–100 and offsets 0–2000. Queries have existing
statement/process timeouts. Unsupported inputs reject; unavailable access returns
sanitized 503 with no fixture fallback. Responses retain no-store handling.

The local-only factory rejects non-loopback peer addresses, forwarded/proxy headers,
non-local Host and external origins. It permits only the dedicated loopback UI
origins on port 5181. RequestGuard gained an optional per-instance origin tuple;
its original default remains unchanged for all other factories. Existing authenticated
account routes, JWT verification, role rules, Model A/B/C and Hybrid contracts are
unchanged. This local anonymous viewer is approved only for these synthetic rows;
it does not authorize private health data or provide genuine Admin/Doctor sessions.

Do not bind publicly, tunnel, proxy or deploy this factory. Default/public factories
cannot enable it through environment alone. No public deployment was attempted.

## Acceptance evidence

- Actual PostgreSQL reader catalog: 2,852 rows; 1,332 observations; 666 per mission.
- Nine focused tests passed, including traversal of all 1,332 observations, stable
  pagination, no duplicates, scope filtering, provenance, quality, read-only role
  permissions, RLS activation, default disablement and normal-factory absence.
- Wrong role/remote configuration rejected; external peers, Host, Origin and proxy
  headers rejected; Auth/private-profile reads and owner-role switching denied.
- No-data-change fingerprint reconfirmed. Auth users remain zero.
- Chrome actual API-to-UI acceptance passed: all labels, queried counts, 42 default
  heart-rate rows and chart, environmental Pa values, 100-row page navigation,
  no duplicate adjacent-page IDs, mission switching and direct refresh. Eight
  actual viewer API responses were 200; no JavaScript exceptions. No fixture API
  or precomputed inference result was used for acceptance.
- Combined backend: **833 passed, 32 skipped, 1 deselected**. Legacy database tests
  that create Auth substitutes and copied seeding-write tests are disabled; the
  estimator-fitting test is deselected with the no-training guard. Existing AI,
  M2, Hybrid and qualification contracts are unchanged.
- Frontend: **197 passed, 1 skipped**; new five-test viewer client/default/error
  suite also rerun after the final visual fix. TypeScript and production build pass.
  The build audit finds no fixtures/test modules/dataset/model assets.
- Ruff and formatting pass (144 files), strict mypy passes (136 files plus direct
  provisioning-script check), dependency consistency and whitespace pass.
- Protected worktree HEAD/branch/status/source hashes and artifact hashes checked
  separately. No source, model or seed changes were made in the protected sources.

Focused backend verification:

```sh
cd "$HOME/CAREYONDA-seeded-dashboard/backend"
CAREYONDA_RUN_SYNTHETIC_VIEWER_TESTS=1 \
 PYTHONPATH=/tmp/careyonda-remediation-deps \
 "$PYTHON" -m pytest tests/integration/test_synthetic_viewer.py -q
"$PYTHON" -m ruff check . ../simulator scripts/configure_synthetic_reader.py
"$PYTHON" -m ruff format --check . ../simulator scripts/configure_synthetic_reader.py
PYTHONPATH=/tmp/careyonda-remediation-deps "$PYTHON" -m mypy
PYTHONPATH=/tmp/careyonda-remediation-deps "$PYTHON" -m mypy scripts/configure_synthetic_reader.py
```

Full regressions keep `CAREYONDA_TEST_DATABASE_URL` and
`CAREYONDA_SEED_TEST_DATABASE_URL` unset, use the above viewer test opt-in,
`PYTHONPATH=/tmp:/tmp/careyonda-remediation-deps`, `-p model_b_no_training`, and
`-k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'`.
No dependencies were installed. Existing Python 3.12.10/Node 24.21 environments
and temporary HTTP/test overlay are separately provisioned, not committed.

## Remaining limits

This is an intentionally local synthetic research viewer, not Supabase activation,
user authentication, an operational mission assignment service, a complete patient
dashboard, or an AI inference source. Model B remains canonically unassessed;
Model A historical NASA and Model C self-report workflows are independent.
No synthetic seed observation is fed automatically to an AI model or combined with
historical NASA. No production view or public deployment candidate was overwritten.

The database is ephemeral local development infrastructure. Preserve/review it
before any separately authorized cleanup. Do not automatically remove policies,
regenerate data or activate a different database. Publication covers reviewed source,
tests and documentation only; it does not enable a public viewer.

## Exact changed-file inventory

- `backend/app/api/security.py`
- `backend/app/api/synthetic_viewer.py`
- `backend/app/application/synthetic_viewer.py`
- `backend/app/schemas/synthetic_viewer.py`
- `backend/app/seeded_main.py`
- `backend/app/storage/demo_seed.py`
- `backend/app/storage/synthetic_viewer.py`
- `backend/scripts/configure_synthetic_reader.py`
- `backend/tests/integration/test_demo_seeding.py`
- `backend/tests/integration/test_synthetic_viewer.py`
- `backend/tests/unit/test_demo_seed.py`
- `docs/demo/SEEDED_DASHBOARD.md`
- `docs/demo/SYNTHETIC_DATA_DEMO.md`
- `frontend/src/app/App.tsx`
- `frontend/src/app/ConnectedWorkspace.tsx`
- `frontend/src/features/synthetic-database/SyntheticDatabase.test.tsx`
- `frontend/src/features/synthetic-database/SyntheticDatabase.tsx`
- `frontend/src/infrastructure/synthetic-database.ts`
- `frontend/src/main.tsx`
- `frontend/src/shared/ui.tsx`
- `simulator/demo_seed.py`

The local `frontend/node_modules` symlink is excluded from the checkpoint.
