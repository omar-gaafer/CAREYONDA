# CAREYONDA frontend — API-only operational workspace

The production frontend discovers the existing local backend's capabilities and
fails closed for unsupported data sources. It displays **no generated telemetry,
fictional crew, demo incidents or precomputed model outputs**. The current backend
advertises synthetic-only observations/M2 and no authentication, so operational
monitoring and real-person health access remain unavailable. All twelve routes show
explicit capability, connection, source and authorization states.

The official navy/teal brand assets, black/white/neon-green design, responsive sidebar,
keyboard navigation and route titles are preserved. Nothing is stored in localStorage,
sessionStorage, IndexedDB or cookies. No runtime CDN, telemetry, cloud model or
external dependency download is used.

## Runtime and commands

Use Node **22.12–24.x** (verified on Node 24.21.0). The existing `package-lock.json`
pins dependencies. Provision dependencies before offline execution; this audit did
not install or change dependency versions.

```sh
cd frontend
npm ci       # installation step only when provisioning is authorized
npm run dev -- --port 5173 --strictPort
npm run typecheck
npm test
npm run format:check
npm run build
```

`npm run build` performs strict TypeScript/build checks and production-bundle review.
It writes ignored `dist/` artifacts and a relative `production-modules.json` inventory.
Build fails if test harnesses/fixture modules enter the runtime graph; the post-build
review additionally rejects retained demo presentations and fixture sentinel strings.
Re-run the artifact review with `node scripts/verify-production-bundle.mjs`.

Serve locally from a documented backend CORS origin, normally
`http://127.0.0.1:5173` or preview port `4173`. Production static hosting must return
`index.html` for all application routes, but not for missing assets. No service worker
or cold-launch cache is installed. Backend disconnection yields explicit unavailable
views, never a fixture fallback.

## Backend connection and safety

`VITE_API_URL` defaults to `http://127.0.0.1:8000`; provision another approved loopback
origin via `.env.local` or the build environment. Only credential-free HTTP origins on
`127.0.0.1`/`localhost` are accepted, without path/query/fragment. This is public build
configuration, not secret storage. Start the existing backend according to
[LOCAL_API_V1.md](../docs/api/LOCAL_API_V1.md).

Production requests only GET `/api/v1/capabilities`, with no credentials, no-store,
redirect refusal and a ten-second timeout. It validates contract version 1.0.0,
capability names/availability, `medically_validated=false` and `none_local_only` auth.
The UI distinguishes available components from simulation-only research components
and absent/unimplemented capabilities. A component reported available does not
establish authorization, measured-source compatibility or clinical validation.

Refresh is explicit; there is no continuous-connectivity claim. Retrieval time is
browser metadata-fetch time, not acquisition time. A failed refresh invalidates stale
metadata. There is no invented observation freshness threshold. Crew/time controls
are disabled until supported authorized context and observations exist.

## Routes and architecture

All twelve approved paths remain: `/overview`, `/health`, `/environment`,
`/ai-intelligence`, `/incidents`, `/assistant`, `/crew`, `/analytics`,
`/recommendations`, `/data-explorer`, `/digital-twin`, `/reports`.
`/` redirects to `/overview`; unknown paths show an unavailable route view.

- `src/app/`: production shell, capability discovery state, explicit module gates,
  API-only composition and route metadata.
- `src/contracts/capabilities.ts`, `src/infrastructure/capabilities.ts`: strict
  current API capability boundary and safe read-only client.
- Existing observation/M2 contracts and HTTP research adapter are preserved without
  expanding their synthetic-only source envelope to measured records.
- `src/testing/`: isolated deterministic fixtures and historical research workspaces.
  These are imported by tests only; no production route or environment switch exposes
  them. The retained research feature files are also outside the production graph.
- `src/shared/`: reusable layout, official branding, UTC formatting and existing
  tested evidence/chart widgets. No source values or diagnoses are invented.

## Tests, limitations and audit

Tests distinguish API-only operational behavior from preserved research regressions.
They cover all routes, strict capability validation, network/permission/schema
failures, missing capabilities, stale refresh/retry, empty pages, synthetic-only
transport limitations, no browser persistence, original evidence/provenance,
chart gaps, M2 abstention/safety, official branding and keyboard focus.
Browser acceptance exercises the production build against the existing local API.
No successful measured-data or fitted-model execution is claimed.

Read the [full dependency inventory](FRONTEND_DATA_AUDIT.md),
[model readiness and backend blockers](MODEL_READINESS.md), and
[implementation/verification report](OPERATIONAL_VERIFICATION_REPORT.md).
The recorded [pre-change Git status](audit/working-tree-before.txt) identifies preserved
uncommitted work. Phase 1/2/3 and UI/branding reports are historical records; their
fixture-mode startup instructions no longer describe the production entry point.
