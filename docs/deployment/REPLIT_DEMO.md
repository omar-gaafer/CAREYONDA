# Replit public synthetic demo candidate

Base: frozen application `2b073fcfe63a53c9af02ea048501f5c19faeae7b`.
The frozen branch and all existing worktrees are preserved. This candidate selects
the explicitly permitted frontend-only public fallback. It is not a public deployment
of the research API and does not claim unified live AI inference.

## Diagnosis and decision

The existing Python backend works. Its root 404 is normal; health, capabilities and
OpenAPI exist. Its clients and RequestGuard deliberately require loopback origins.
Simply binding that app publicly, changing CORS to `*`, or exposing Vite would either
fail or remove intended protections. Local-only endpoints also accept self-reports;
this milestone does not add the authentication and policy system needed for that
public workflow. No backend import repair was necessary.

Smallest safe public architecture: a Node production server serves only the compiled
synthetic frontend from a checked build manifest. It has no Python process, API proxy,
model loader, training/evaluation runner, database, private file mount or submission
endpoint. Browser API mode is removed from this build. The Python backend is unchanged
and remains private. Local Model C API and stale-session tests still pass.

## Public capability boundary

- Dashboard, monitoring, evidence explorer and M2 investigation examples: synthetic,
  precomputed fixtures. Session-only review state is not operational alert handling.
- Model A: explicitly unavailable; no simulated successful inference is substituted.
- Model B: explicitly unassessed; canonical threshold approval remains pending.
- Model C: private/unavailable; no personal-data form or public submission.
- Hybrid and adapters: private research/CLI only. No historical NASA evidence is
  joined to prospective astronaut observations.
- Every public view carries PUBLIC SYNTHETIC DEMO. No fixture is claimed as telemetry.

Only `GET/HEAD /api/v1/health` and `/api/v1/capabilities` return public metadata.
Capabilities explicitly state `none_public_synthetic_only` and `no_research_backend`;
they are not the private API's local-only capability contract. All research paths,
including `/openapi.json`, are denied. POST is always 405. Unlisted files are 404,
not SPA fallbacks. Direct known UI routes and refresh return the compiled index.

## Replit setup

1. Import the GitHub repository and select `feature/replit-demo-preparation`.
   Verify its commit against the delivery report. Do not import local folders,
   virtual environments, NASA data, receipts, artifacts or private `.env` files.
2. Use Node **24** (locally tested 24.21.0). `.replit` requests `nodejs-24` and both
   build/start fail closed on other Node majors. Confirm that runtime module in the
   Replit editor; platform provisioning has not been executed by this task.
   Python is not needed in the public candidate. Private research was tested on
   Python 3.12.10; do not substitute Python 3.14 for trained-model work.
3. Build command from repository root:

   ```sh
   npm --prefix frontend ci
   node deployment/build.mjs
   ```

   `npm ci` provisions only existing package-lock dependencies. No dependency was
   installed during local preparation. The build script forces VITE_PUBLIC_DEMO=true,
   ignores VITE_API_URL, runs TypeScript/Vite and copies only compiled assets into
   ignored `deployment/public/`, with a public-only manifest. Do not use plain
   `npm run build` as the publication artifact: local mode is intentionally different.
4. Select Autoscale publishing with the `.replit` build/start settings. Public start:

   ```sh
   node deployment/server.mjs
   ```

   The server binds **0.0.0.0**, respects assigned **PORT**, default 5000, and maps
   local 5000 to external 80 in `.replit`. Expose only this process. Do not launch
   Uvicorn or a Vite development server in the public deployment.
5. Health check: `GET /api/v1/health` -> 200 with `public_synthetic_only`.
   `GET /` must return 200 HTML. Verify the actual published HTTPS URL in a new
   browser tab, direct `/environment`, `/model-c`, `/ai-intelligence`, then refresh.
   The iframe-denial policy intentionally requires opening Replit Preview in a
   separate tab; do not remove it just to embed the app in an editor frame.
6. Verify `/api/v1/model-c/local-assessments` and `/openapi.json` are inaccessible,
   and POST `/api/v1/investigations` returns 405. Confirm Model A unavailable,
   Model B unassessed, no API mode switch, no browser errors. Only then share URL.

Replit configuration/ports reference:
https://docs.replit.com/features/project-setup/configuration
Publishing types: https://docs.replit.com/features/publishing/deployment-types
The local candidate is tested; no Replit account settings or hosted URL were verified.

## Environment and secrets

| Variable | Purpose |
| --- | --- |
| PORT | Assigned listening port; integer 1–65535, default 5000 |
| VITE_PUBLIC_DEMO | Forced true by public build, not a runtime setting |
| VITE_API_URL | Ignored by public build; leave unset |

No secret is required for this isolated anonymous synthetic demo. Do not add model
paths, acquisition receipts or credentials. Any future authenticated private API
must undergo separate review and keep credentials in Replit Secrets, never VITE_*
variables, source or compiled browser assets.

## Security limits

Read-only asset allowlist; bundle capped at 10 MB/64 assets and 2 MB per file;
realpath checks reject symlink escapes. Only compiled HTML/JS/CSS are loaded, never
the repository root. Correlation IDs, no-store, nosniff, CSP, no-referrer, denied
iframes and camera/microphone/geolocation are applied. Same-origin module requests
work; cross-origin requests are rejected with no CORS grants. Shared links may
navigate to a top-level document. There are no cookies or user accounts.

Limits per server process: 240 requests/minute, 32 simultaneous connections,
8 KiB headers, 2048-character URLs, 5-second timeouts. Requests with bodies reject;
no inference/submission computation is possible. Limiting is global/per-process,
not authenticated per-user or distributed DDoS protection. Replit infrastructure,
account cost controls and HTTPS termination remain operator responsibilities.

## Verification and reproduction

From root after existing dependencies are provisioned:

```sh
node --test deployment/server.test.mjs
node deployment/build.mjs
PORT=5000 node deployment/server.mjs
```

PowerShell: `$env:PORT="5000"; node deployment/server.mjs`.
Frontend: `npm --prefix frontend test`, `npm --prefix frontend run typecheck`.
Backend (private environment, from backend): existing no-training regression command
in `docs/research/AI_I5_DEMO_FREEZE.md`; Ruff/formatting, strict mypy and pip check.

Acceptance: server isolation tests, public frontend regression tests, production
build, real Chrome direct navigation/refresh, no off-origin/research-API requests
or console errors. Existing private backend regressions are reproduced separately;
public Model C submission is intentionally unavailable, not falsely marked passed.
No model was loaded, retrained or changed. No generated build/evaluation output is
committed. This candidate is safe for anonymous **synthetic-only** publication with
this exact production entrypoint; private research execution is not authorized.

## Remaining deployment actions

Actual Replit runtime provisioning, publishing and HTTPS URL acceptance require
operator access and have not been performed. If Node 24 is not offered, stop and
verify another runtime separately; do not silently use unsupported Node/Python.
For judges, show synthetic views and evidence inspection; demonstrate Model C and
Hybrid separately in the private research environment if required. This public demo
is not clinical validation or operational safety decision support.
