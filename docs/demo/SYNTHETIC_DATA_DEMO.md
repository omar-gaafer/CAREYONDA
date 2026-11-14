# Synthetic mission database seed — local fallback v1.0.0

Status: **local disposable PostgreSQL seeded and verified; no remote Supabase
seeding or genuine Auth integration performed**. The owner's hold on Supabase
configuration/connectivity remains in effect. The protected configuration path
was not read or assumed to exist. No credentials were requested or printed.

## Workspace and schema

Branch `feature/demo-seeding`, based on protected checkpoint
`fcea4af2ab6c9c065ae5da5747d64c1acf9eb5cd`. All development is isolated in
`CAREYONDA-demo-seeding`; existing worktrees and qualification remain protected.

Reviewed schema: `supabase/migrations/20261114120000_initial_schema.sql`;
SHA-256 `1ef0d939bec205860527c68d3f2cd0b5ee80cb95bd6d08c380e2d4bec5e5e4b4`.
The unchanged migration and verification SQL reproduced 35 tables, 58 foreign
keys, RLS enabled on all 35 tables, and zero client RLS policies on PostgreSQL 18.
Observation contract remains 1.0.0. No new columns, policies or migrations were added.

A new socket-only local cluster/database was created for this task:

- Socket directory: `/tmp/careyonda-seeding-socket`, port 55438.
- Database: `careyonda_demo_seed_local`.
- Network listening disabled (`listen_addresses=''`); host authentication rejects.
- Initially all application-data tables were empty; only the migration's metric
  registry was populated. A minimal **empty** `auth.users(id uuid)` table exists
  solely for the migration's FK definition. No Auth user row was inserted,
  impersonated, or used as an authentication substitute.

This local compatibility schema is not Supabase Auth and cannot verify JWTs.
The seed tool rejects remote hosts, non-socket targets, database names outside
`careyonda_demo_seed_*`, populated Auth tables, unexpected application data,
non-default client policies, schema count differences and drifted existing seeds.
It must not be repurposed to target Supabase without a separately reviewed workflow.

## Actual inserted rows

First run: **2,852 rows**. Second run: **0 rows**, unchanged fixture digest and
counts. Ten existing tables receive seed rows:

| Table | Rows |
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

The four measurement subtypes sum to 1,332. Observation quality is 1,156 valid,
72 suspect conflict records, and 104 missing records. Quality reason rows include
both missingness and conflict reasons. Missing values never become zero or normal.

No rows were added to `auth.users`, `profiles`, `user_roles`, `doctor_profiles`,
`doctor_astronaut_assignments`, `mission_crew_assignments`,
`mission_spacecraft_assignments`, inference/evaluation tables or investigations.
No model artifacts or model metadata were seeded. No trained model was loaded.

The suggested three doctors and one administrator are **blocked**, not fabricated.
Doctor profiles and assignment grantor fields require genuine Auth-backed profiles.
The six fictional astronauts have null `user_id`, as permitted by the schema;
they have no login entitlements. Mission/subject IDs in observations preserve
synthetic scope but do not confer authorization or replace assignment rows.

## Generation and provenance

`simulator/demo_seed.py` reuses the existing M1.2 mission generator. Seed 42,
version 1.0.0, namespace `synthetic-demo-v1`; UUID record keys derive deterministically
from unique observation IDs. The six astronauts are split three per fictional
mission, with separate fictional ships and cabins.

Six scenario blocks per astronaut:

1. Synthetic baseline activity — not a medically normal reference.
2. Increased synthetic CO2 with toy associated physiological variation.
3. Reduced sleep with explicitly reported synthetic fatigue.
4. Recent exercise — an existing simulator scenario, not a diagnosis.
5. Missing heart-rate/sleep observations.
6. Simultaneous conflicting heart-rate reports, marked suspect.

Each block has six one-minute event steps; blocks are separated by one day from
fixed UTC epoch 2026-01-01. Simulated ingestion delays are preserved separately.
These timestamps describe a synthetic experiment, not factual acquisition of
real-world measurements. All origins are `simulated`, source type `simulator`,
with explicit scenario/run/generator/seed metadata. No raw NASA data are used.

Canonical units: heart rate `bpm`; cabin CO2 partial pressure `Pa`; sleep `h`;
communication delay `s`; exercise boolean; fatigue categorical
`rested`, `tired`, `very_tired`. Pa is not converted to NASA CO2 ppm. All numerical
relationships and example values are simulator assumptions, not clinical
thresholds, validated physiology, hazard limits or exposure-response laws.
No derived observation lineage is invented; records are original simulator outputs
with empty parent references. Source IDs and simulation lineage survive storage.

Seed-42 fixture SHA-256:
`7e7cc664f88dff71b8a51110a30dbf529206c7dafd939a9d09a62dfa4fbd93d1`.
Database-owned creation timestamps are not part of this deterministic fixture hash.

## Safe seed command

Use the existing provisioned Python 3.12.10 environment. No package installation
is needed or performed. The local database must first have the reviewed migration;
the seed command never runs migrations itself.

```sh
cd "$HOME/CAREYONDA-demo-seeding/backend"
export PYTHON="$HOME/CAREYONDA-model-b-python312/bin/python"
PYTHONPATH=.:.. PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m app.storage.demo_seed \
  --database 'host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local' \
  --seed 42 --confirm-disposable
```

Run it twice: repeated seeding verifies exact stored values and inserts zero rows.
A changed seed requires a new empty disposable database; existing records are not
updated, deleted or silently reused. The runner performs exact content/count
checks, obtains an advisory lock and table locks, applies all inserts in one
transaction and re-verifies values afterward. Database constraint failures roll back the
write transaction; a post-write verification mismatch is reported and never
automatically repaired. Generated summaries are local temporary outputs, not Git data.

## Verification commands and results

```sh
cd "$HOME/CAREYONDA-demo-seeding/backend"
export CAREYONDA_SEED_TEST_DATABASE_URL='host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local'
PYTHONPATH=/tmp:/tmp/careyonda-remediation-deps PYTHONDONTWRITEBYTECODE=1 \
  "$PYTHON" -m pytest tests/unit/test_demo_seed.py tests/integration/test_demo_seeding.py -q
"$PYTHON" -m ruff check . ../simulator
"$PYTHON" -m ruff format --check . ../simulator
PYTHONPATH=/tmp/careyonda-remediation-deps "$PYTHON" -m mypy
```

- Focused seed suite: **19 passed**.
- Combined backend: **831 passed, 25 skipped, 1 deselected**. The 16 legacy
  PostgreSQL tests that directly fabricate `auth.users` are explicitly disabled
  by leaving `CAREYONDA_TEST_DATABASE_URL` unset. The other existing opt-in skips
  remain, and the estimator-fitting test is deselected with the external
  no-training guard enabled. No retraining occurred.
- Frontend: **192 passed, 1 skipped**; TypeScript production build and fixture-free
  production module audit passed. No frontend sources changed.
- Ruff, formatting (136 files), strict mypy (130 files), dependency consistency,
  SQL verification and Git whitespace checks pass.
- Existing repository readback exactly equals supported original numeric seed
  observations, including UTC times, units, quality, source and simulation metadata.
- Mission filter returns no observations for the wrong mission/astronaut pair.
- All 35 RLS flags and zero policies remain. A dedicated NOLOGIN SQL reader
  granted SELECT sees **zero observations**, without disabling/bypassing RLS.
- Directly constructed role labels without actual DB profiles/grants have zero
  entitlements for Admin, Doctor and Astronaut. These are negative policy tests,
  not authenticated user sessions or genuine Auth verification.
- Existing account API remains 503 without configured genuine authentication.
  Anonymous research observation endpoints retain their separate configured
  synthetic source and expose **none** of the seeded database records.
- The unchanged actual M2 engine processed compatible elevated-CO2, reduced-sleep,
  missing and contradictory windows deterministically. Those software tests do
  not establish clinical validity; no results were stored or hardcoded as inference.
- Model B's canonical status remains unassessed; no AI code or research contracts
  changed. All protected worktrees and artifacts are checked for integrity.

Full backend command uses `env -u CAREYONDA_TEST_DATABASE_URL -u CAREYONDA_ENABLE_DATABASE`,
the above seed-test database variable, `-p model_b_no_training`, and
`-k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'`.
The no-training guard and HTTP/test dependency overlay are previously provisioned
external verification tools under `/tmp`, not package/runtime additions.

## Actual frontend availability

The latest inherited frontend exists in this worktree, unchanged from the final
integration checkpoint. Its `/account` view can display bounded authorized numeric
records only after genuine token verification and server-side assignments exist.
It is not a health-chart or mission-list integration. Current results:

- No seeded records are displayed through authenticated UI: genuine users and
  assignments are absent, and Supabase remains unverified.
- Operational mission/dashboard charts remain unavailable; no mission-list or
  database chart endpoint was invented.
- Model A historical replay and Model C local self-report workflows remain
  independent of this seed. Existing synthetic M2 demo sources are separate.
- Existing frontend regressions cover loading/unavailable/error and session
  invalidation. No browser claim of seeded chart display is made.
- Inference history, investigation persistence and categorical/missing record
  retrieval are not implemented by the current account numeric-read slice.

Do not label the existing local fixture dashboard or original M2 presets as these
new database records. No silent fallback or cross-source merge was introduced.

## Remote activation requirements

The owner's Supabase provisioning hold remains. When explicitly lifted:

1. Verify the disposable project and matching Auth/DB identities; inventory its
   actual schema/data before any writes. Do not assume a config file exists.
2. Create genuine test users through supported Supabase Auth administration.
   Never insert `auth.users` directly or reuse local SQL identity stubs.
3. Provision reviewed profiles/roles, three doctor relationships, six astronaut
   identity mappings, mission memberships and genuine grantors using those users.
4. Review a separate remote seed path; this runner intentionally rejects remote
   targets and any Auth-populated target. Never remove its guards to make tests pass.
5. Verify actual Admin/Doctor/Astronaut token flows, expiry, cross-user/mission
   rejection and protected record round trips. Preserve default-deny browser RLS.

## Cleanup — not executed

The seed tool has no deletion or cleanup mode. For this fully disposable local
cluster, an operator may separately authorize dropping only
`careyonda_demo_seed_local` after checking its identity, ownership and contents.
Never apply a cleanup command to Supabase or a shared database by changing a DSN.
Stop the dedicated local cluster when no longer needed:

```sh
/usr/lib/postgresql/18/bin/pg_ctl -D /tmp/careyonda-seeding-pg stop
```

After separate explicit disposal approval, the operator can use `dropdb` against
that exact local socket/port/database, or dispose of this dedicated cluster.
No database, dataset, source file, artifact or protected worktree was deleted by
this task. No commit or push occurred.
