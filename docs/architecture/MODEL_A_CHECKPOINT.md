# Local Model A integration checkpoint (M-A.6)

## Scope and baseline provenance

This is a local checkpoint on `feature/model-a-integration`, not a merge or an
upstream release. Parent commit: `bfc19cbdeab9e71cb1ab16d4e62e954d2ef4969c`.
The reproducible source tree necessarily includes a snapshot of previously
uncommitted M2/M3/M4.2 and frontend development from `/home/darknight90/CAREYONDA`.
Those components were not present as committed upstream code at that parent.

`MODEL_A_BASELINE_SNAPSHOT.json` identifies 27 original backend/documentation
files and their pre-integration SHA-256 hashes; `MODEL_A_FRONTEND_SNAPSHOT.json`
identifies 45 frontend files and their original hashes. The checkpoint inventory
classifies unchanged snapshot files and integration overlays separately.
M2 behavior and M4.2 contracts remain unchanged from those original snapshots.
Omar's loader, model contract, artifact storage, Model A dependency pins, test
fixtures and loader tests originate from commit
`e86cda00fac8bb359164173d8d24ed0bf2f7aa90`.

The durable registered worktree is `/home/darknight90/CAREYONDA-model-a-integration`.
A cross-filesystem `git worktree move` was unavailable. A complete copy was
verified against source hashes, then registered with `git worktree repair`.
The previous `/tmp/CAREYONDA-model-a-integration` remains a backup with its `.git`
pointer renamed `.git.pre-ma6-backup`; do not use it as the active worktree.
Historical manifests and acquisition receipts retain their original paths.
The original development worktree's 71 dirty files, status and branch are
verified independently; the checkpoint does not commit or modify that worktree.

## Contents and exclusions

`MODEL_A_CHECKPOINT_INVENTORY.json` is the exact changed-file inventory relative
to the parent, including SHA-256, size and provenance category. It inventories
itself without a recursive checksum; Git's commit tree authenticates that file.
Use `git show --stat HEAD` and `git diff HEAD^ HEAD --name-only` for Git inventories.

Includes source, deterministic artificial fixtures, tests, dependency pins and
lockfile, API/frontend contracts and provenance documentation. Synthetic test
fixtures are artificial, not NASA measurement exports. Excludes NASA datasets,
fitted artifacts, actual evaluation outputs, local acquisition receipts, private
configuration, environments, caches, build outputs and temporary browser evidence.
Real measurement values, scores and private artifact paths are not embedded in
the frontend. Source examples use artificial estimators and values only.
No remote branch is updated by this checkpoint.

## Reproduction

Provision dependencies separately; runtime remains offline. Tested Python:
3.12.10; Model A requires the exact pinned scikit-learn/NumPy/joblib versions.
Tested Node 24.21.0/npm 12.2.0; supported Node range is in package.json.
From the checkpoint root (commands below use a POSIX shell):

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-model-a-integration.txt
npm --prefix frontend ci
cd backend
.venv/bin/python -m uvicorn app.model_a_main:create_app --factory --host 127.0.0.1 --port 8000
```

In a second terminal, from the root:

```sh
VITE_API_URL=http://127.0.0.1:8000 npm --prefix frontend run dev
```

Without server-side ModelAConfig, startup succeeds and API mode explicitly
reports Model A unavailable. Fixture mode is visibly simulated. A scored replay
requires a separately provisioned trusted artifact, validated environmental rows,
and factual local acquisition receipts registered in server-side configuration.
Follow `../api/MODEL_A_ENVIRONMENTAL_API_V1.md` and
`MODEL_A_HISTORICAL_REPLAY.md`; HTTP callers cannot authorize receipts or supply
artifact paths. Local smoke composition/receipts are deliberately not committed.
Never use event time as source ingestion time or turn NASA CO2 ppm into Pa.

Quality commands, from backend (then return to root for frontend):

```sh
.venv/bin/python -m pytest
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy --strict app tests ../simulator
.venv/bin/python -m pip check
cd ..
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run format:check
git diff --check
```

No packages were installed during M-A.6. Verification used existing isolated
Python dependencies and existing node_modules. The staged source was also
materialized separately to verify that no ignored source files were needed.

## Verification and browser acceptance

Backend: 124 focused Model A tests passed; full suite 419 passed, 2 expected
local-data skips. Ruff lint/format, strict mypy (73 files) and pip check passed.
Frontend: 106 passed, 1 expected optional local smoke skip; typecheck, production
build and Prettier passed. The separately enabled real API-to-React-DOM smoke
also passed, with runtime response assertions rather than persisted real scores.
Build emits two existing nonfatal upstream Zod annotation warnings.

Real Chrome 156.0.8078.79 was used against the production frontend preview and
local backend, with the existing trusted artifact and actual acquisition receipt.
Passed: visibly simulated fixture mode and artificial flagged state; genuine API
historical replay with not_flagged score/threshold, original mission time, replay
acquisition time and explicit unknown historical availability; real 403 invalid
sample and 422 invalid input show safe errors without fixture fallback; actual
unconfigured backend shows unavailable without stale results; M2 investigation
view and its separate API submission remain operational and independent.

Browser acceptance is PARTIAL: abstained and incompatible-artifact UI states were
not exercised in Chrome because no approved missing-data sample was available
and the trusted artifact was not modified. These cases have automated coverage;
that coverage is not claimed as browser acceptance. No statistical score is a
clinical risk, diagnosis, severity or calibrated confidence.

## Remaining boundaries

The checkpoint can be shared only after separately authorized push. It does not
include licensed NASA data, fitted artifacts or replay authorization; provision
those independently under their existing access/reuse constraints. Model B still
needs an approved training/inference contract, a verified artifact/runtime and an
isolated adapter/test path. Existing M4.2 research contracts are not a substitute
for Model B inference. NASA environmental measurements must not be represented as
paired astronaut physiology or contemporary exposure. No Model B implementation,
new algorithm, retraining, API redesign or remote operation is part of M-A.6.
