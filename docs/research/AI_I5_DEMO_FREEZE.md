# AI-I5 application demo freeze

Base: AI-I3 `31887bc812411a563833e775ccb3320b7cc59ea7`. No branch merge.
Model C application source restored from `aecc38f7461a5d61f9e5c415cd8d2d9ac985d151`:
API, application use case, standalone factory, local-entry schema, backend tests,
frontend client/contracts/panel/fixtures/tests and navigation. Existing Model C
research implementation and temporal validation remain unchanged. UI request-generation
invalidation for Clear session, participant/input changes and delayed responses is
preserved; only startup guidance changes. No model algorithms or M2/M4.2 contracts change.

## Composition and public contract

`app.demo_main:create_app` combines existing synthetic M2, optional Model A and
Model C `POST /api/v1/model-c/local-assessments` under the existing bounded,
loopback-only HTTP boundary. Original factories remain available. Model A startup,
authorized catalog and receipt checks are reused; no HTTP caller supplies paths.

Capabilities API v1.0.0 gains additive availability member `unavailable`.
In the Model A/combined factories, `trained_models` now reflects current Model A
availability. `model_a_environmental_api` indicates route support;
`model_c_transient_sleep_fatigue_research` indicates deterministic workflow support.
All are medically unvalidated. The base factory still reports no trained-model
integration of its own. Consumers must tolerate the additive enum member.
Model A sidecar stays v1.1.0. Capability overrides are injected at composition time.

Synthetic Model A display replaces fixture-internal NASA/ISS/real declarations with
simulated provenance labels; API provenance and strict response validation remain
unchanged. No API error falls back to a simulated result. Offline Model C mode
never fabricates an assessment.

Model C local entries are transient self-reports, not NASA or wearable telemetry.
The original contract labels manual form submissions `real`; this describes actual
form entry, not independently verified truth. For demos use a synthetic participant
and announce synthetic values. Entries are not persisted. The original noon-UTC
reporting/support-interval convention is preserved. Missing fatigue abstains
independently of sleep. No historical acquisition timestamp is invented.

## Launch

Use previously provisioned dependencies: Python 3.12.10 and frontend Node
22.12 through 24. Declarations: backend/pyproject.toml and frontend/package-lock.json;
existing resolved requirements remain available. This milestone installs nothing.
Dependencies/artifacts must be provisioned separately; runtime performs no downloads.

From repository root, separate terminals:

```sh
cd backend
python -m uvicorn app.demo_main:create_app --factory --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm run dev -- --port 5173 --strictPort
```

Alternatively run `npm run build`, then
`npm exec vite preview -- --host 127.0.0.1 --port 4173 --strictPort`.
Use only allowed origins 5173/4173; switching to an occupied-port fallback such as
5174 causes origin rejection. Do not disturb another server to free a port.

Open `/overview`, `/environment`, `/model-c`, `/ai-intelligence`.
Select Local API for submissions. Default Model A: unavailable, empty authorized
catalog, 503 assessment. Real replay needs explicit server-side ModelAConfig,
trusted separately provisioned artifact, authorized samples and factual receipts.
No fitted model was loaded during this acceptance.

Model C demo: participant `synthetic-demo-a`; enter 17 consecutive past dates with
sleep cycling 7.0/7.1/7.2 hours and assessment period 3 days. These are software-demo
values, not physiological limits. Earlier 14 days form the reference. Leave fatigue
blank to demonstrate independent abstention. Submit, inspect evidence and limitations,
Clear session, enter `synthetic-demo-b`: previous results must disappear. No threshold
is approved by this demo. Real self-report data must never be committed or logged.

## Research demonstration

From backend with research/dev dependencies:

```sh
PYTHONPATH=.:.. python -m examples.temporal_evidence
PYTHONPATH=.:.. python -m examples.hybrid_evidence
PYTHONPATH=.:.. python -m examples.research_adapter_demo
PYTHONPATH=.:.. python -m examples.ai_h3_evaluation
```

PowerShell: set `$env:PYTHONPATH=".;.."`, then run the Python commands.
Fixtures are explicitly synthetic. Adapter demo uses a fake Model B estimator,
not fitted-model evaluation. Model B stays unassessed without canonical approval;
NASA replay stays quarantined from prospective astronaut evidence. Fatigue stays
categorical context. No new Model B/Hybrid endpoints. H3 A/B/C are ablations,
not model identities.

## Verification

- Backend: 796 passed, 9 skipped, one estimator-training test deselected.
- Frontend: 143 passed, one optional local-asset test skipped.
- Model C UI: 35 passed, including delayed A response after Clear/B entry.
- TypeScript/build, Ruff/formatting, strict mypy (116 files), dependency consistency
  and whitespace checks passed. No packages installed.
- Frozen AI-H3 JSON matches exactly: 13 challenges, 12 eligible, one rejection,
  12/12 M2 invariance. I3 preserves cross-subject rejection, replay quarantine,
  Model B unassessed state and unchanged M2.
- Headless Chrome production-build acceptance: corrected fixture labels, actual API
  Model A unavailable state, Model C synthetic self-report submission with scored
  sleep/abstained fatigue, session reset, M2 view rendering. Pending-request races
  additionally covered by the deferred-response frontend regressions.
- Existing worktree branches, HEADs, statuses and inventoried hashes unchanged.

Backend reproduction (from backend):

```sh
python -m pytest -q -k 'not test_isolation_forest_scores_are_deterministic_and_rank_outlier_high'
python -m ruff check --no-cache . ../simulator
python -m ruff format --check --no-cache . ../simulator
python -m mypy
python -m pip check
```

Do not opt into estimator fitting. Local NASA/replay tests intentionally require
separate opt-in. Frontend: `npm test`, `npm run typecheck`, `npm run build`.
Git: `git diff --check`.

## Judge-facing scope and remaining limits

Show synthetic dashboard, actual deterministic M2 investigations, honest optional
Model A availability and executable sleep/fatigue research using synthetic entries.
Show Hybrid via CLI. Do not claim unified live A/B/C/Hybrid inference, clinical
validation, a validated isolation/confinement detector or operational safety.
Canonical Model B threshold approval and trusted Model A asset provisioning remain
external requirements. No datasets, fitted artifacts, local receipts or generated
evaluation outputs are included. Stop at this application freeze.
