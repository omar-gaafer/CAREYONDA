# Final local integration candidate

Status: **verified local research application; partial authenticated persistence;
not approved for public or production health use**. No commit, merge or push.

## Source selection and old frontend diagnosis

| Component | Selected source | Reason / boundary |
| --- | --- | --- |
| Base backend/research | `2b073fcfe63a53c9af02ea048501f5c19faeae7b` | Demo freeze includes verified AI-I3 `31887bc812411a563833e775ccb3320b7cc59ea7`, Model C API/UI fixes and unchanged M2/M4.2 |
| Frontend shell/navigation/twin | original worktree snapshot based on `a292941` (`origin/feature/frontend-3d`) | Newer capability-driven UI, brand assets, responsive navigation and interactive illustrative spacecraft twin; original additional App/modules/styles/test changes preserved in copied snapshot |
| Model A/C UI | verified demo-freeze source retained | Newer frontend branch does not carry these workflows; explicitly restored into newer shell without replacing its layout |
| Model A replay startup/acquisition | reviewed uncommitted `feature/real-data-demo` files | Actual asset loader, integrity verification and factual acquisition receipts; originals untouched |
| Database | `7d16b6a2159434ff85c35ddccbe86c744796dc53` | Copy unchanged initial schema, verification and design documents; verifier count corrected separately |
| Qualification | unchanged protected uncommitted report | Copied SHA-256 `10637f5e288d799924d3ce3e3068f4e717b0042b615f10cc24bbe1d93cd33244`; owner review still pending |

The prior real-data demo intentionally began at demo freeze, not the divergent
frontend branch (common ancestor `bfc19cb`). Therefore it retained the older
research workspace shell. Commit dates were not used as the selection criterion:
source inventories, actual route composition and tests established the difference.
The newer frontend deliberately replaced simulated operational displays with
capability/unavailable states. Those protections remain; genuine research
workflows are restored through separate explicit contracts. No directories were
blindly replaced and no protected source files were modified.

`SOURCE_SELECTION.json` records copied file origins and source hashes where
applicable. `FINAL_FILE_INVENTORY.json` records the complete changed source/test/
configuration/documentation inventory and final hashes, excluding generated
artifacts and the local dependency symlink. New integration edits are distinct
from copied previously uncommitted snapshots; none is represented as upstream.

## Architecture and contract changes

```text
Latest React shell (API-only, runtime-validated responses)
  -> existing loopback FastAPI + optional account router
       -> research: original Model A/C, synthetic M2, separate H1/H2/H3/I3 CLI
       -> account: Supabase Auth verification -> active DB roles/assignments
                   -> optional PostgreSQL numeric records repository
```

- Presentation remains in `app/api`; authentication/persistence use cases in
  `app/application/authorized_records.py`; providers in `app/storage`.
- No AI algorithm, M2 ranking, M4.2 schema or trusted artifact was changed.
- Existing research routes and capability contract still report
  `none_local_only`: they are unauthenticated synthetic/local research. Separate
  `/api/v1/account/*` routes require actual verified Supabase bearer identity.
  Do not interpret research capability discovery as account authorization.
- Account identity is UUID from Supabase `/auth/v1/user`, not decoded client JWT
  claims or client-selected roles. Auth calls have HTTPS origin validation,
  explicit timeout, no redirects and sanitized errors. Tokens stay in frontend
  memory only. Sign-out/input changes invalidate pending responses.
- Database connection is server configuration only; no browser database client or
  service key exists. The optional adapter uses preinstalled `/usr/bin/psql`,
  bounded subprocess/statement timeouts, escaped SQL literals with standard
  strings, transactional writes and fixed bounded queries. This avoids installing
  a new driver for this hackathon slice. It is not a connection pool and should
  be replaced behind the repository protocol before scaled deployment.
- `httpx>=0.28,<1` is now an explicit runtime dependency for optional Supabase
  identity verification; it was already provisioned, so no install occurred.
- Existing CORS origins remain limited to loopback 4173/5173. Only the Authorization
  request header was added at the final composition root; no public origins.
- New frontend capability validation accepts `unavailable`, already present in
  the backend contract. Model A core no longer imports a fixture; the historical
  fixture wrapper remains only for isolated tests. Build graph checks still reject
  all fixture/test modules. A bundle sentinel was narrowed from a legitimate
  enum string to an embedded precomputed-payload marker; all other sentinels remain.

## Database implementation and permissions

The unchanged migration was executed on PostgreSQL 18 in two fresh disposable
local databases, using a minimal synthetic `auth.users` stub (not Supabase Auth).
Verified: **35 tables, 58 foreign keys, 35 RLS-enabled tables, zero client policies**.
Eight actual unique constraints reproduced; the supplied verifier incorrectly
expected five. Only its expected count changed, not the migration.

RLS was tested after granting authenticated SELECT in the disposable database:
profiles and observations both returned zero visible rows. Direct browser access
remains default-deny. No migration was applied to production/Supabase.

Implemented table use:

- `profiles`, `user_roles`: active identity and unrevoked grants.
- `doctor_profiles`, `astronaut_profiles`, `doctor_astronaut_assignments`,
  `mission_crew_assignments`: current role/subject/mission authorization.
- `missions`: Admin-only creation.
- `observations`, `numeric_measurements`, `observation_quality_reasons`:
  atomic numeric, non-derived astronaut Observation v1 persistence and retrieval,
  preserving event/ingestion times, quality, source and simulation provenance.
- Existing metric definition/scope/unit FKs and deferred measurement integrity
  constraints remain enforced by PostgreSQL.

Admin still requires a valid target astronaut/mission association. Doctors require
an active doctor-patient assignment; astronauts require their linked identity.
Writes also require assignment at observation event time, no future event or
availability, and factual ingestion supplied by the acquisition caller. Astronaut
writes are restricted to self-report origin. Source claims are declarations, not
sensor attestation. Unsupported scopes/types/derived lineage are rejected rather
than discarded. Reads are explicitly bounded to the earliest 100 numeric,
non-derived astronaut records; this is not complete dataset export.

**Partial / blocked:** genuine Supabase credentials are absent. Supabase protocol
verification is covered by mock transport tests; real identity-provider/project
connectivity and issued-user end-to-end login are unverified. Role tests substitute
identity only inside tests, while using actual PostgreSQL for roles, assignments,
reads and writes. The running app therefore returns 503 for account operations;
it does not activate fake users or roles. No password sign-in/signup workflow,
role assignment administration, offline identity/sync, full observation variants,
assessment history or normalized investigation persistence is implemented.
The schema lacks approved browser policies and operational identity/grant policy.
Production credentials/least-privilege grants, DB/Auth project binding, privacy,
retention, auditing and concurrency/load review remain deployment blockers.

## Verified AI execution

| Component | Execution / limitations |
| --- | --- |
| A | Actual pinned v1.1.0 Isolation Forest loaded through existing loader; API-to-Chrome NASA historical replay scored `0.4924359938661092`, threshold `0.5736639144466789`, not_flagged. Original 2014 mission event retained; actual local replay receipt recorded after verified acquisition; historical ingestion remains unknown. CO2 ppm never becomes Pa or contemporary human exposure. |
| B | Actual pinned v1.0.0 fitted pipeline reproduced 780/780 saved scores and experimental flags; maximum difference 0, absolute/relative tolerance 1e-12; 4 partially imputed. All canonical outputs remain unassessed. CLI execution, not a new scoring API. Owner threshold approval pending. |
| C | Actual existing API engine assessed synthetic, non-sensitive browser entries; clear session removed the result. Existing deferred-response regressions pass. Genuine self-reports pending; not a validated isolation/confinement detector. |
| H1/H2 | Existing separate synthetic temporal/evidence association examples executed. No NASA/synthetic participant joint context was fabricated. |
| H3 | Frozen 13-case challenge reproduced, 12 eligible, one boundary rejection, M2 invariant 12/12, provenance 56/56, zero unsupported directional assertions. A/B/C in this evaluation name configurations, not the three trained model identities. |
| I3 | Existing adapter regressions pass; historical replay quarantine, unassessed B and contextual C restrictions preserved. |

Model A and B remain CONDITIONALLY_QUALIFIED exactly as recorded in the copied
Phase 1 report. Research qualification is not clinical or NASA operational approval.

## Working routes

Frontend: all latest navigation routes remain, including overview, health,
environment, AI intelligence, incidents, assistant, crew, analytics,
recommendations, digital twin, data explorer and reports. Unsupported operational
pages remain honestly unavailable. Added `/sleep-fatigue` and `/account`.

- `/environment`: real server-authorized Model A replay, independent of crew.
- `/sleep-fatigue`: actual existing Model C submission and session reset.
- `/ai-intelligence`: API-executed synthetic M2 with ranks, evidence inspection,
  uncertainty and explicit unassessed safety.
- `/analytics`: accurate Model B/Hybrid research availability, no fabricated score.
- `/digital-twin`: latest interactive illustrative twin, not live telemetry.
- `/account`: verified-token entry and scoped record UI; currently reports unavailable.

Backend retains health, capabilities, contexts, synthetic observations and M2
investigations; authorized environmental catalog and anomaly-context POST; Model C
local assessment POST. New account routes:

- `GET /api/v1/account/me`
- `GET /api/v1/account/observations?mission_id=...&astronaut_id=...`
- `POST /api/v1/account/observations` (supported Observation v1; 201 on commit)
- `POST /api/v1/account/missions` (Admin only; 201)

All account failures are sanitized 401/403/422/503 with existing correlation IDs
and no-store handling; no filesystem paths are accepted from callers.

## Verification

- Backend: **828 passed, 9 skipped, 1 deselected** with model fitting blocked.
  The deliberately deselected existing test fits an Isolation Forest; initially
  the guard rejected it, then it was explicitly excluded rather than permitting
  training or changing its assertion. Skips cover opt-in artifacts/datasets and
  existing training-only checks; separate actual A/B executions passed.
- 16 actual PostgreSQL integration tests pass: role boundaries, cross-mission,
  read/write, rollback, future evidence, suspended identity and unavailable state.
- 10 Supabase protocol/CORS tests pass; no real credentials used.
- Frontend: **192 passed, 1 skipped**, including new account race/error tests and
  retained Model A/C regressions. Existing route assertions were updated for
  restored real workflows and two new routes, not removed to hide failures.
- Strict mypy: 126 files; Ruff lint/format: 132 files; TypeScript, production build,
  production module/fixture audit, pip dependency consistency and whitespace pass.
- Chrome: latest shell/twin, actual A API inference, actual C API synthetic entry,
  session clear, M2 API-rendered ranks/evidence, B unassessed, unavailable account;
  no runtime JavaScript exceptions. Direct routes/refresh initialize correctly.
- Original qualification report, artifact hashes, and all protected worktree
  HEAD/branch/status/source hashes checked against the initial inventory.

Actual receipts, model outputs, browser evidence and PostgreSQL clusters remain
outside Git in a temporary local session. No artifact/dataset was copied here.
Local node_modules is a provisioned dependency symlink, not source to publish.

## Start the verified local candidate

Existing separately provisioned environment: Python 3.12.10, NumPy 2.4.6,
scikit-learn 1.9.1, joblib 1.6.0, SciPy 1.17.1; Node 24.21.
No dependencies were installed. Existing HTTP/test overlay must remain provisioned
or be restored from reviewed dependency declarations before repeating commands.

```sh
export FINAL_ROOT="$HOME/CAREYONDA-final-integration"
export PYTHON="$HOME/CAREYONDA-model-b-python312/bin/python"
export PYTHONPATH=/tmp/careyonda-remediation-deps
export PYTHONDONTWRITEBYTECODE=1
export CAREYONDA_TRUSTED_LOCAL_MODEL_A=1
export CAREYONDA_MODEL_A_ARTIFACT="$HOME/CAREYONDA-Omar/artifacts/model_a/nasa_rr1_iforest_v1.1.0_rs42"
export CAREYONDA_NASA_DATASET="$HOME/CAREYONDA/datasets/processed/nasa_rr1_eda_d2d3_validated"
export CAREYONDA_REPLAY_RECEIPT_DIR=/tmp/careyonda-final-session/receipts
cd "$FINAL_ROOT/backend"
"$PYTHON" -m uvicorn app.final_main:create_app --factory --host 127.0.0.1 --port 8108
```

In another terminal:

```sh
cd "$HOME/CAREYONDA-final-integration/frontend"
VITE_API_URL=http://127.0.0.1:8108 npm run build
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/environment`. The prior protected real-data demo remains
separate on its existing ports; do not confuse it with this selected frontend.

Optional genuine database configuration, backend secrets only:

```sh
export CAREYONDA_ENABLE_DATABASE=1
# Set in protected operator environment, not source or browser:
# CAREYONDA_SUPABASE_URL=https://<actual-project>.supabase.co
# CAREYONDA_SUPABASE_PUBLIC_KEY=<project public key>
# CAREYONDA_DATABASE_URL=<same-project PostgreSQL DSN with required TLS>
```

Do not point this candidate at production or run migrations without approval.
The DB login must have reviewed backend-only privileges; RLS grants remain denied
to browser clients. Obtain tokens through actual Supabase Auth. User/profile/role
and assignment provisioning require approved administrative setup, not a client role.

Research CLI:

```sh
cd "$HOME/CAREYONDA-final-integration/backend"
"$PYTHON" -m app.storage.model_b_smoke \
 --artifact "$HOME/CAREYONDA-model-b-integration/artifacts/model_b/seed42-q95-final" \
 --dataset "$HOME/CAREYONDA/datasets/synthetic/m1_2_seed42" \
 --expected-artifact-sha256 c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e \
 --expected-manifest-sha256 2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132 \
 --trusted-local-artifact
"$PYTHON" -m examples.temporal_evidence
"$PYTHON" -m examples.hybrid_evidence
"$PYTHON" -m examples.ai_h3_evaluation
```

Regression reproduction (disposable DB only):

```sh
cd "$HOME/CAREYONDA-final-integration/backend"
# Optional actual database tests; the DB must already contain Ahmed's migration.
export CAREYONDA_TEST_DATABASE_URL='host=/tmp/careyonda-final-pg-socket port=55437 dbname=postgres'
PYTHONPATH=/tmp:/tmp/careyonda-remediation-deps "$PYTHON" -m pytest \
 -p model_b_no_training -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high' -q
"$PYTHON" -m ruff check . ../simulator
"$PYTHON" -m ruff format --check . ../simulator
"$PYTHON" -m mypy
cd ../frontend
npm test
npm run typecheck
```

The no-training guard is external verification infrastructure, not a runtime
feature; preserve it or separately provision an equivalent guard before rerunning.
Do not point integration tests at a protected database: their fixtures write
explicitly synthetic users/assignments/observations. PostgreSQL test auth.users
is merely a schema stub and must never be presented as genuine authentication.

## Release blockers and next actions

1. Owner review this uncommitted candidate and partial scope. No source publication
   or merge is authorized until the combined report is reviewed.
2. Provision an approved disposable Supabase project, actual Auth users/assignments
   and least-privilege backend DB credentials. Verify genuine sign-in/token lifecycle
   and account API/UI end-to-end; no claim of production auth integration yet.
3. Approve authorization/privacy/retention/audit policy before protected records or
   public exposure. Implement broader persistence only after those decisions.
4. Ahmed must approve Model B's canonical threshold policy separately; keep unassessed.

The application is ready for **local research demonstration**, not a completed
production clinical platform or public authenticated health service.
