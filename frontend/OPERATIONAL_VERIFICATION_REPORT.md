# API-only frontend — implementation and verification

Date: 2026-11-14. Current branch remains `feature/hazard-reasoning`.

## Result

Production is API-only and capability-driven. It requests the current backend's
capability metadata and never imports the synthetic fixture repositories, old demo
presentations, precomputed results or fictional crew. There is no mode switch or
fallback. All twelve approved routes and root redirect remain accessible. Unsupported
source/model/authorization states are explicit; no operational values were invented.

The current API is synthetic-only and unauthenticated, so **operational telemetry,
real-person health access and operational inference remain disabled**. Available
component metadata does not override those contract limits. This milestone prepares
a trustworthy integration boundary; it does not implement measured-data/model
services. The separate Model A worktree was inspected, not imported or modified.

The existing research UI was preserved in `src/testing/ResearchWorkspace.tsx`, with
explicit test-only providers and a historical synthetic HTTP harness. Existing feature
presentations remain available to those deterministic tests, outside the production
graph. No fixture JSON or pre-existing file was deleted. The same evidence/provenance,
quality/gap, M2 ranking/abstention/safety and manual research-workflow tests still run.

## Actual verification

Existing dependencies only: Node 24.21.0, Vite 7.3.8, Vitest 3.2.7. No packages were
installed and no dependency versions/lockfile were changed.

| Command / check | Result |
| --- | --- |
| `npm run typecheck` | Strict TypeScript passed |
| `npm test -- --reporter=dot` | **121 passed**, 9 test files; final run 5.46 s |
| `npm run format:check` | Passed for source/configuration/HTML |
| `npm run build` | TypeScript + production build + bundle review passed; Vite 2.36 s |
| `node scripts/verify-production-bundle.mjs` | Passed; **12 rendered frontend source modules**, no test/demo feature modules or fixture sentinels |
| `node_modules/.bin/prettier --check scripts/verify-production-bundle.mjs` | Passed |
| `git diff --check` | Passed |

Two nonblocking Rollup annotation warnings come from the existing Zod dependency;
the build succeeded. There is no configured frontend ESLint command, so no ESLint
pass is claimed. Backend tests/model inference were not rerun: no backend/model
implementation changed. Local runtime capability behavior was independently exercised
through the actual existing backend during browser acceptance.

The final tests include all 87 prior deterministic research/branding tests, now
explicitly isolated, plus 34 operational/boundary cases. They cover all twelve routes,
no production mode selector, no unauthorized subject access, synthetic-only capability
gating, empty capabilities and observation pages, measured-envelope refusal,
connection/permission/schema/version errors, non-sensitive error text, pending actual
requests, stale-refresh invalidation/retry, no browser storage writes, browser-offline
semantics, navigation focus and drawer keyboard trapping. Existing tests retain
original units/timestamps/provenance, missing/invalid readings and null chart gaps,
original M2 evidence/ranking, conflict/insufficient/abstained results and safety status.

## Production browser acceptance

Actual installed local Chrome and an already cached Playwright driver were used
without downloading anything. Short-lived local backend and production-preview
processes were started and stopped by the check. The user's existing port 5173
service was left untouched; preview used documented allowed origin port 4173.
No datasets, fitted artifacts or subject records were loaded by the UI.

Passed checks:

- All twelve route links, root redirect, route titles and keyboard focus after changes.
- Desktop 1440px, collapsed sidebar, tablet 768px, mobile 390px and mobile drawer.
- No horizontal document overflow; official image loading and aspect ratios preserved.
- Mobile drawer focus trap, Shift+Tab cycling, Escape and focus return.
- Actual backend capability request; **the only backend path requested was
  `/api/v1/capabilities`**, with no observation/context/investigation/model requests.
- Backend process shutdown followed by refresh: disconnection is explicit and prior
  capability snapshot is invalidated as stale.
- Intercepted artificial 403 and unsupported-version responses: permission denial and
  contract mismatch are explicit and raw response details are not reflected.
- Browser local/session storage entries remained zero.

The initial system Playwright package lacked its Node driver. The already installed
cached driver was used successfully instead; no browser-check dependency was added
to the project. A first focus assertion incorrectly expected focus reset when clicking
the already-current route; it was corrected to check actual route changes. These
are verification-harness corrections, not evidence of successful measured inference.
Screenshots were inspected from `/tmp/careyonda-operational-*.png`; no generated QA
files were added to application assets. This does not replace a screen-reader audit
or establish clinical/operational validation. No model-running success can be
truthfully exercised through this production app until model access is authorized.

## Production bundle review

`vite.config.ts` now rejects imports from testing/fixture paths and test modules when
emitting production chunks. `scripts/verify-production-bundle.mjs`, included in the
build command, additionally rejects retained research presentations and distinctive
fixture strings (fictional crew, demo mission ID, waveform/source identifiers and
precomputed-case origin). The rendered source inventory is generated at
`dist/production-modules.json`, containing only relative source paths.

The reviewed graph contains App/ConnectedWorkspace, modules/access/discovery state,
capability schema/client, observation validation vocabulary, main entry, shared layout,
branding and styles. Observation vocabulary is static contract metadata, not data.
The historical JSON, test generators/providers, research hooks and feature screens
are absent. The tiny 0.03-kB charts chunk is a residue of the pre-existing manual
chunk configuration, not bundled telemetry or synthetic charts.

## Preservation and changed files

The original working-tree status is in `audit/working-tree-before.txt`. A temporary
SHA-256 inventory of 170 pre-existing source/documentation/data files was compared
at completion: **116 files outside frontend were unchanged**, no pre-existing file
was removed, fixture JSON and official PNGs were unchanged, and the package lock was
unchanged. Other research worktree Git status remains clean. No branch switch,
staging, commits, pushes, merges or rebases occurred. Existing unrelated dirty backend
and root README work remains as found.

Modified source/configuration/documentation files:

- `PHASE2_CONTRACT_MAPPING.md`
- `PHASE2_IMPLEMENTATION_REPORT.md`
- `PHASE3_INTEGRATION.md`
- `README.md`
- `index.html`
- `package.json`
- `src/app/App.test.tsx`
- `src/app/App.tsx`
- `src/app/ConnectedWorkspace.tsx`
- `src/app/modules.ts`
- `src/app/redesign.test.tsx`
- `src/contracts/observation.test.ts`
- `src/features/health/Health.tsx`
- `src/features/incidents/Incidents.tsx`
- `src/features/investigations/Intelligence.tsx`
- `src/features/investigations/phase2.test.tsx`
- `src/features/overview/Overview.tsx`
- `src/infrastructure/http.test.tsx`
- `src/infrastructure/investigations.ts`
- `src/infrastructure/observations.ts`
- `src/shared/BrandLogo.test.tsx`
- `src/styles.css`
- `vite.config.ts`

Added files:

- `FRONTEND_DATA_AUDIT.md`
- `MODEL_READINESS.md`
- `OPERATIONAL_VERIFICATION_REPORT.md`
- `audit/changed-files.json`
- `audit/working-tree-before.txt`
- `scripts/verify-production-bundle.mjs`
- `src/app/moduleAccess.ts`
- `src/app/operational.test.tsx`
- `src/app/useCapabilities.ts`
- `src/contracts/capabilities.ts`
- `src/infrastructure/capabilities.ts`
- `src/testing/ConnectedResearchWorkspace.tsx`
- `src/testing/ResearchWorkspace.tsx`
- `src/testing/investigations.ts`
- `src/testing/observations.ts`

Ignored generated `dist/` output and `tsconfig.tsbuildinfo` were refreshed by the
required build. They are generated artifacts, not manual source changes.
`audit/changed-files.json` records before/after hashes for changed pre-existing files
and hashes for additions, excluding its own self-reference and generated output.

## Remaining blockers and next task

See `MODEL_READINESS.md` for the full matrix and backend blockers, and
`FRONTEND_DATA_AUDIT.md` for route/file/source/action/test inventory. Authentication,
authorized subject/mission context, compatible measured observation transport,
mission status, deployed model contracts/capabilities, incident APIs, approved
procedures, twin metadata and historical/report retrieval are still absent.

The next task is a separately reviewed backend contract milestone for authorized
measured/context data, or controlled Model A integration with its approved artifact,
catalog and factual receipt provenance. Do not enable real-person access or import
another worktree's fixture panel merely to make these views look operational.
