# Local real-data research demonstration

This uncommitted demonstration extends the frozen application checkpoint
`2b073fcfe63a53c9af02ea048501f5c19faeae7b` on `feature/real-data-demo`.
It is local-only, requires separately provisioned trusted assets, and makes no
clinical or NASA operational validation claim. No model was retrained.

## What actually runs

- Model A: actual fitted environmental Isolation Forest v1.1.0, historical NASA
  RR-1 ISS measurements. Three authorized test samples are resolved from the
  validated export, including observation IDs and feature lineage. Original
  NASA ingestion remains null/unknown. CO2 stays ppm, not synthetic Pa.
- Model B: actual fitted synthetic health Isolation Forest v1.0.0 on 780 synthetic
  held-out records. All saved scores and experimental decisions reproduced;
  maximum absolute score difference 0, tolerance absolute/relative 1e-12.
  Canonical results remain unassessed for all 780 records. The recorded q95,
  NumPy higher, strict greater-than policy is experimental, not owner-approved.
- Model C: actual deterministic API engine assessed explicitly synthetic,
  non-sensitive sleep/fatigue entries. Genuine self-reports remain pending.
  Manual-entry provenance does not authenticate the truth of entered values.
- H1/H2: separate, explicitly synthetic deterministic research examples. NASA
  replay is not joined with synthetic participants or prospective health data.

NASA inputs were manually exported from the official NASA EDA for RR-1. The
original download timestamp and release-specific download record are not known.
This task does not republish data or establish new redistribution permission.
Raw telemetry has 12,087 records and radiation 39; the validated export retains
separate radiation quantities and ground controls. Only ISS environmental test
features enter Model A; no human exposure pairing is asserted.

## Trust and acquisition

The startup factory verifies a pinned artifact digest, compatible numerical
runtime, model metadata, pinned dataset manifest, all manifest-covered payloads,
exact feature schema, original unknown ingestion, and observation lineage.
The existing trusted loader performs estimator loading and scoring unchanged.
Only after reading and verifying the local dataset does acquisition code record
actual UTC acquisition, with a second integrity check. Each startup creates a
new metadata-only receipt outside the repository. It never backfills historical
NASA ingestion or uses file modification time as evidence availability.
Receipts use logical source references rather than exposing filesystem paths.
Missing/incompatible configuration leaves Model A explicitly unavailable.

Pinned SHA-256:

| Asset | SHA-256 |
| --- | --- |
| Model A model.joblib | f6b28b9d2e5925d0a568eba79bb0d3af516e31a8cbc7d96725ef86dfd85c44b6 |
| NASA export manifest | 40005d13160fdf2ea729237f965508fd2864ac1e187a3dcf8753f7cdf928706b |
| Model B pipeline | c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e |
| Model B artifact manifest | 2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132 |

## Start locally

Use the existing isolated Python 3.12.10 environment with NumPy 2.4.6,
scikit-learn 1.9.1, joblib 1.6.0 and SciPy 1.17.1, plus the declared backend HTTP
and test dependencies. Frontend was verified with Node 24.21 and existing
provisioned dependencies. No packages were installed by this task.

Set local paths (these are operator configuration, never HTTP parameters):

```sh
export CAREYONDA_ROOT="$HOME/CAREYONDA"
export DEMO_ROOT="$HOME/CAREYONDA-real-data-demo"
export PYTHON="$HOME/CAREYONDA-model-b-python312/bin/python"
export PYTHONPATH=/tmp/careyonda-remediation-deps
export PYTHONDONTWRITEBYTECODE=1
export CAREYONDA_TRUSTED_LOCAL_MODEL_A=1
export CAREYONDA_MODEL_A_ARTIFACT="$HOME/CAREYONDA-Omar/artifacts/model_a/nasa_rr1_iforest_v1.1.0_rs42"
export CAREYONDA_NASA_DATASET="$CAREYONDA_ROOT/datasets/processed/nasa_rr1_eda_d2d3_validated"
export CAREYONDA_REPLAY_RECEIPT_DIR=/tmp/careyonda-real-data-session/receipts
cd "$DEMO_ROOT/backend"
"$PYTHON" -m uvicorn app.real_data_main:create_app --factory --host 127.0.0.1 --port 8107
```

In another terminal, using the same DEMO_ROOT:

```sh
cd "$DEMO_ROOT/frontend"
VITE_REAL_DATA_DEMO=true VITE_API_URL=http://127.0.0.1:8107 npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open `http://127.0.0.1:4173/environment`, select an authorized sample and click
**Assess Model A**. Direct navigation/refresh works with the Vite preview SPA.
The dedicated build starts in API mode; normal builds retain fixture default.
Synthetic dashboard plots stay explicitly separate from the real NASA panel.
Do not switch to fixture mode and describe its simulated Model A output as real.

Existing API routes:

- `GET /api/v1/health`
- `GET /api/v1/environmental/authorized-samples`
- `POST /api/v1/environmental/anomaly-context`
- `POST /api/v1/model-c/local-assessments`

Use only server-issued authorized references for Model A. The existing API
validates receipt trust, bounded input, acquisition/assessment ordering and
schema/units. It does not accept client artifact paths. Keep binding loopback;
this unauthenticated research application is not a public deployment candidate.

Run actual Model B reproduction separately:

```sh
cd "$DEMO_ROOT/backend"
"$PYTHON" -m app.storage.model_b_smoke \
  --artifact "$HOME/CAREYONDA-model-b-integration/artifacts/model_b/seed42-q95-final" \
  --dataset "$CAREYONDA_ROOT/datasets/synthetic/m1_2_seed42" \
  --expected-artifact-sha256 c4434929f380687abdc6318ef8954b10972d9b19941e20308d3134c0bacd595e \
  --expected-manifest-sha256 2c31f1e3e2ad12e781ad7e9ebe72512600744d1334d57051d1d6d9a52cee5132 \
  --trusted-local-artifact
"$PYTHON" -m examples.temporal_evidence
"$PYTHON" -m examples.hybrid_evidence
```

The last two commands are synthetic research demonstrations, not actual NASA or
human telemetry. Model B is a CLI demonstration, not a newly integrated UI/API.

## Acceptance evidence

- Backend: 802 passed, 9 expected skips, 1 training-related deselection, using
  the external no-training guard. Separate actual-artifact executions succeeded.
- Frontend: 143 passed, 1 expected skip; TypeScript production build passed.
- Strict mypy: 119 files; Ruff lint and formatting: passed (125 formatted files).
- Dependency consistency and Git whitespace: passed.
- Chrome headless actually rendered API-backed NASA score
  0.4924359938661092 versus threshold 0.5736639144466789, not_flagged;
  event 2014-10-25T20:51:00Z, replay acquisition 2026-11-14T11:11:53.625582Z,
  assessment 2026-11-14T11:15:08.317000Z, historical availability unknown.
  These are measured run results, never hardcoded runtime outputs.
- The other two measured scores were 0.4903565918456101 and
  0.49589258796470803, also not_flagged. No flagged result was fabricated.
- Actual Model C API returned assessed for explicitly synthetic entries;
  browser acceptance in this task covered the real NASA panel. Existing UI
  regression tests cover Model C submission and stale-response invalidation.
- All 13 preexisting worktrees matched their initial HEAD, branch, status and
  source hashes. The uncommitted qualification report was preserved unchanged.

Generated outputs and acquisition receipts are under a local external temporary
session directory, not Git. No model artifacts or measurements were copied into
this worktree. No commit or push was performed.

## Remaining limitations

No real human self-reports were supplied. Model B policy approval remains with
Ahmed. NASA historical source availability is unknown; local acquisition only
permits retrospective replay. Models do not establish clinical validity,
causality, astronaut exposure, or calibrated medical probabilities. H1/H2 are
research-only and no cross-model dashboard association is manufactured.
