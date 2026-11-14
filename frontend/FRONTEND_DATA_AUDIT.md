# Frontend operational-data audit

Audit date: 2026-11-14. Branch: `feature/hazard-reasoning`.
Scope: frontend only; backend/research worktrees were inspected read-only.
The production entry is now API-only. **No operational measurements or model results
are enabled by the currently available backend contracts.** This is a verified
integration blocker, not a claim that empty views constitute functional monitoring.

The pre-change modified/untracked paths are recorded verbatim in
[audit/working-tree-before.txt](audit/working-tree-before.txt). Existing staged state
was empty. No staging, commits, switches, merges or package installation occurred.

## Findings across the twelve routes

| Route | Before: source / classification | Integration readiness and required contract | Implemented disposition / associated tests |
| --- | --- | --- | --- |
| `/overview` | Fixed ARES-07 context, synthetic crew, generated observations, hardcoded launch/demo time, health counts and storyboard event log | No mission/context/status contract; observations API is synthetic-only, not an operational feed | API capability inventory and explicit missing mission/health/environment/incident context; no elapsed time or replacement values. `operational.test.tsx`; prior overview tests remain in test harness |
| `/health` | Fictional crew names/roles and waveform HR/sleep, filtered at fixed demonstration time | AuthN/AuthZ and authorized subject/context plus measured observation envelope required | No authorized health data; no subject data requested. Original quality/gap tests retained in isolated harness |
| `/environment` | Synthetic ppm, Pa, temperature and humidity; static documentation notes for NASA/radiation | Current server has no measured NASA endpoint; Model A worktree is separate | Unavailable source; ppm/Pa distinction and radiation limits retained as reference text. No NASA/synthetic pairing or invented sensor values |
| `/ai-intelligence` | Bundled precomputed M2 cases by default; actual POST M2 in explicit synthetic API mode; frontend displayed supplied ranks, not inference | M2 is implemented but advertised simulation-only; production evidence/auth contracts absent | Operational inference unavailable. Precomputed and submitted research cases remain test-only; exact ranks, abstention, evidence and `not_evaluated` tests retained |
| `/incidents` | Review exercises synthesized from investigation IDs, fake timeline annotations, session-only notes/status | No incident endpoint, independent approved alert policy or persistence contract | Unavailable; no fabricated incidents, timeline or manual workflow in production |
| `/assistant` | Honest static capability description; **no scripted chatbot found** | Grounded assistant endpoint and reviewed evidence/safety boundary absent | Explicit unavailable; no simulated responses |
| `/crew` | Static unavailable view; fictional identities also appeared in global selectors | No authenticated authorized profiles/context service | No authorized profiles; crew selector disabled rather than populated with fictional people |
| `/analytics` | Honest unavailable view; **no fake predictions/confidence found** | No deployed prediction/evaluation endpoint; `trained_models=not_implemented` | Model unavailable; no scores/forecasts generated |
| `/recommendations` | Honest unavailable view; **no fabricated treatment rules found** | Approved versioned procedure source and independent safety policy absent | Guidance unavailable; safety not evaluated |
| `/data-explorer` | Fixture records by default or validated synthetic API pages; original provenance and quality rendered | ObservationPage v1 source is exactly `configured_synthetic`; cannot silently relabel measured records | No operational observations loaded; reviewed evidence widgets remain tested but are not wired to unsupported data |
| `/digital-twin` | Honest capability description; **no live sensor values or trustworthy schematic metadata found** | Geometry/context and sensor contracts absent | Unavailable; no invented schematic/status |
| `/reports` | Honest capability description; **no fabricated report history found** | Historical retrieval, report schema and persistence absent | Unavailable; no invented metrics/history |

Every route remains navigable with its original title, official artwork, accessible
navigation and black/white/neon-green design. Static route names, Lucide module icons,
design tokens and educational unit/limitation text are interface configuration,
not fabricated operational observations. They were not removed as mock data.

## File-level dependency inventory

Paths below are relative to `frontend/`. `T` means isolated deterministic research/test
execution, `P` means production runtime, and `S` means static configuration/reference.
A test fixture declaring measured origin is still artificial software test data.

| Path | Route/feature and data source/type | Readiness / required contract / action | Associated tests |
| --- | --- | --- | --- |
| `src/main.tsx` | P all routes; build-time loopback URL only | Existing browser entry retained; composes API-only workspace | Operational routes + browser acceptance |
| `src/app/ConnectedWorkspace.tsx` | P all; formerly default fixture mode | Replaced source switch with API-only composition; URL changes remount state | `operational.test.tsx` |
| `src/app/App.tsx` | P all; formerly mixed demo shell, crew and observations | Now metadata-only capability shell; no fixture/telemetry imports or model submissions | `operational.test.tsx` |
| `src/app/modules.ts` | S twelve routes/titles/icons | Retained navigation config; descriptions corrected; no capability inferred from route existence | Both operational and retained route tests |
| `src/app/moduleAccess.ts` | P per-route gate; validated capability metadata + explicit contract blockers | `simulation_only` is research-only; `available` is an unvalidated component, not automatic permission or compatible source. No unsupported endpoint is invented | Operational capability tests |
| `src/app/useCapabilities.ts` | P discovery hook; actual network/pending/error state | Read-only no-store metadata; aborts on unmount, safe failure categories; failed refresh invalidates prior metadata | Operational pending/disconnect/stale/retry cases |
| `src/contracts/capabilities.ts` | P capability schema matching backend v1 | Strict version/availability/false medical validation/none-local-auth; duplicate names rejected | Operational boundary cases |
| `src/infrastructure/capabilities.ts` | P GET existing `/api/v1/capabilities` | Credential-free loopback only; no redirect/cache; bounded timeout; no payload logging/persistence; raw errors not surfaced | Operational HTTP options/configuration/error cases |
| `src/infrastructure/observations.ts` | Interface only; former generated fixtures moved to T | `list(): Promise<unknown>` preserved; no runtime implementation/default fixture | Existing observation and HTTP tests |
| `src/infrastructure/investigations.ts` | Interface only; former bundled fixture import moved to T | Optional preset/submit contract retained for research transport tests | HTTP + Phase 2 tests |
| `src/infrastructure/http.ts` | T current synthetic research GET/POST adapter; backend-derived synthetic payloads | Unchanged synthetic-only validation and pagination; not reachable from P; not an authorized measured-data adapter | `http.test.tsx` including real M2-shaped response, empty page, measured-source rejection, errors |
| `src/infrastructure/fixtures/investigations.json` | T four precomputed M2 cases/145 artificial observations | Preserved required test fixture byte-for-byte; only tests/test harness reach it; excluded by build guard | Investigation/Phase 2/HTTP tests |
| `src/testing/observations.ts` | T generator, fictional identities, fixed demo time and filtering | Original deterministic fixture implementation preserved; not an operational provider | `observation.test.ts`, retained App tests |
| `src/testing/investigations.ts` | T precomputed JSON repository | Original precomputed adapter preserved outside P | Phase 2 tests |
| `src/testing/ResearchWorkspace.tsx` | T former shell and fixture/API demonstration | Explicit test-only harness, no application entry/production route; session-only reviews retained for regression | Retained App/redesign/Phase 2/branding tests |
| `src/testing/ConnectedResearchWorkspace.tsx` | T former mode-switch composition | Historical fixture/API workflow retained solely for deterministic transport interaction tests | `http.test.tsx` |
| `src/features/overview/Overview.tsx` | T legacy synthetic dashboard and fixed event story | Excluded from production graph; only test harness imports; no operational mission/status contract exists | Retained App tests |
| `src/features/health/Health.tsx` | T legacy fictional crew + HR/sleep charts | Fixture import points explicitly into testing; excluded from production; requires auth/measured contract before reuse | Retained App filtering/gap tests |
| `src/features/environment/Environment.tsx` | T synthetic charts plus S NASA documentation notes | Excluded from production; no NASA measurements loaded, no implicit ppm/Pa conversion | Retained route/unit tests |
| `src/features/explorer/Explorer.tsx` | T original observation table/inspection/filtering | Excluded until approved operational data contract; preserves event/ingestion times, units, quality and raw provenance | Retained App/redesign provenance/empty/search tests |
| `src/features/investigations/Intelligence.tsx` | T precomputed/API M2 presentation | Supplied ranks/uncertainty only; no browser ranking algorithm. Test-only until a reviewed operational integration | `phase2.test.tsx`, HTTP tests |
| `src/features/investigations/application.ts` | T repository hook, async load/submit, in-memory result snapshots | Excluded from P; no fabricated loading delay; earlier result error behavior is historical research UX only | Phase 2/HTTP tests |
| `src/features/incidents/Incidents.tsx` | T generated review exercises + fictional-name lookup | Explicit test-data import; excluded from P because no incident API | Phase 2 review interaction tests |
| `src/features/incidents/application.ts` | T pure in-memory review reducer | Manual notes bounded; no server persistence; no inferred severity or diagnosis. Preserved, not connected operationally | `application.test.ts` |
| `src/features/capabilities/Capability.tsx` | T historical static roadmap mentioning demo evidence | Excluded from P; replaced operationally by honest per-route capability views | Retained unavailable route tests |
| `src/contracts/observation.ts` | P validation vocabulary; numeric quality confidence is not clinical confidence | Canonical units, quality, origin, event/ingestion semantics unchanged; no measured API authorization inferred | `observation.test.ts` |
| `src/contracts/investigation.ts` | T strict original M2 plus synthetic-only case envelope | Versions, scope, rank/selection, lineage and abstention unchanged; no broadening to measured data | `investigation.test.ts` |
| `src/contracts/api.ts` | T current synthetic-only HTTP envelopes | Unchanged; future measured/auth extensions require backend review first | HTTP boundary tests |
| `src/shared/ui.tsx` | P only layout/badge/UTC helpers; T evidence/Trend/SourceNote exports | Generated-data labels never execute in P; retained chart uses null gaps and `connectNulls=false` | Retained chart/quality tests + bundle sentinel check |
| `src/shared/investigation/components.tsx` | T M2 values, inspection, abstention, fixed storyboard timeline | No production route imports; unchanged supplied evidence/safety; timeline is not a real audit history | Phase 2 evidence/abstention tests |
| `src/shared/Drawer.tsx` | T keyboard details shell; no own data provider | No data fabricated; retained for later reviewed evidence view | Existing Escape/focus-return tests |
| `src/shared/BrandLogo.tsx` | P/S official local artwork | Preserved original pixels, neutral backing, aspect ratio and responsive picture source | Branding + production/browser tests |
| `public/brand/*.png` | S official assets, no measurements | Preserved; neither recolored nor removed | Chrome image/aspect checks |
| `src/styles.css`, `src/design-tokens.css` | P/S design/layout | Theme and existing accessibility retained; only capability layout/disabled-control rules added | Format + browser layouts |
| `src/vite-env.d.ts` | S environment typing | No data source or credentials | TypeScript |
| `src/test-setup.ts` | T jsdom observers/layout stubs | Test-only geometry, not simulated operational success | All jsdom tests |
| `src/**/*.test.ts*` | T deterministic artificial inputs/mock HTTP | Original fixtures preserved; production cases explicitly use ConnectedWorkspace, historical research cases explicitly use testing harness | 121 tests final run |
| `scripts/generate_investigation_fixtures.py` | T development-time Python M2 fixture export | Preserved and not executed in this audit; no runtime inference in browser | Existing contract/regression fixtures |
| `scripts/verify-production-bundle.mjs` | Build artifact audit only | Reads sanitized module inventory and JS; rejects test/demo sentinels; no network or sensitive data | Executed with production build |
| `vite.config.ts` | S/build plugins/chunks/test config | Build fails for testing/fixtures/test-module leakage; emits relative source module inventory | Production build |
| `package.json`, `package-lock.json`, `tsconfig.json` | S toolchain | Existing stable dependencies/lock/strict TS retained; build now also audits bundle, no package installation | Typecheck/build/format |
| `index.html`, `.env.example`, `.gitignore` | S metadata/public config | Description now API-only; official favicon/title references preserved; URL is public config, never credentials | Browser/title checks |

No store library, service worker, browser database, automatic fixture fallback on
network failure, external telemetry, remote model, artificial timer-driven success,
scripted assistant, fake clinical confidence, fake forecast or fabricated treatment
implementation was found. Prior default fixture mode was explicit demo behavior,
not a transport fallback; it still made the production app depend on synthetic
records. That default and production mode control have now been removed.

## Production policy and capability behavior

The only production data request is GET `/api/v1/capabilities`. All operational
observation/model access stays disabled because available contracts cannot satisfy
source and authorization requirements. `available` in a capability catalog is not
permission to fetch health records or proof of a compatible measured-data envelope.
Unknown/new versions and auth declarations fail explicitly; no schema was broadened.

The response distinguishes `available` (component, unvalidated), `simulation_only`
(research-only) and `not_implemented`. A missing capability is not treated as success.
Empty catalogs show no advertised capability. All twelve routes still work on loading,
errors and denied access. Retry is a real network request. Failed refresh hides the
previous snapshot and labels it stale, rather than showing it as current. Snapshot
retrieval time is actual browser fetch completion, not an observation timestamp.
No arbitrary clinical freshness cutoff is invented. Browser-offline is not equated
with loopback-backend failure.

No source measurements are requested or cached. No subject data, raw errors,
credentials or source payloads are put in browser persistence, logs or URL parameters.
Production does not offer M2 submission, so it cannot imply model-running or successful
inference. Existing research-only running/error/abstention/insufficient-evidence/
conflict/safety displays remain regression-tested; operational model-running states
cannot be truthfully activated until a reviewed model endpoint is connected.

The bundle build guard rejects imported `src/testing`, fixture paths and test modules.
`production-modules.json` records the rendered frontend source graph. A separate
post-build check also rejects historical demo feature modules and distinctive fixture
strings. These controls prevent accidental reintroduction; they are not a proof that
all future payloads will be authentic or clinically valid.

## Source restrictions reviewed

Reviewed Phase 2 mapping/report, Phase 3 integration, backend API contracts/routes,
M2 docs, M4.2 contracts/decisions, NASA D2/D3 and training handoff. NASA export/source
permission remains unverified for redistribution. No raw NASA CSV, generated export,
artifact, checkpoint or clinical record was copied to the frontend. NASA environment
is an unpaired ISS environmental stream, not astronaut physiology. Synthetic episodes
are separate scenarios, not longitudinal personal baselines. Daily radiation has
limited temporal precision; accumulated-dose source units remain unresolved.

Model A integration source/docs in `/home/darknight90/CAREYONDA-model-a-integration`
were accessible and inspected read-only. No imports, copies, executions, merges or
modifications of that worktree were made. Checkpoint/report statements are described
as source evidence, not independently rerun inference.

See [MODEL_READINESS.md](MODEL_READINESS.md) for exact model readiness and backend
blockers, and [OPERATIONAL_VERIFICATION_REPORT.md](OPERATIONAL_VERIFICATION_REPORT.md)
for executed checks and scope preservation.
