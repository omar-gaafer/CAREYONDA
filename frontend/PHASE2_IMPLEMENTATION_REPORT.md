# Phase 2 implementation report

Delivered 2026-11-13, locally in `frontend/` on `feature/hazard-reasoning`. Existing Phase 1 source was extended; all 39 regression tests are retained. No backend, simulator, dataset or research documentation was edited. The three modified backend files and four untracked M2 files retain their original Git status/diff summary. No branch switch, staging, commit, push or publication occurred.

## Delivered

- Functional `/ai-intelligence`: synthetic investigation selector, selected astronaut/mission, explicit current/reference windows, evidence counts and quality, ranked compatibility hypotheses, selected pattern or abstention, human-readable explanations, supporting/contradicting/missing evidence, expected relations, complete lineage, uncertainty, original versions, and unchanged `not_evaluated` safety status.
- Clickable evidence IDs open focused, keyboard-dismissable original observation details with units, scope, timestamps, quality, source origin and provenance. Unresolved references produce an explicit error at the payload boundary.
- Functional `/incidents`: synthetic list/detail, shared crew context, workflow-status filter, demo severity/category labels, associated investigation links, acknowledgement, manual notes, workflow closure and reopening. Workflow statuses never modify reasoning or safety. Notes and statuses live only in App memory and survive route navigation until reload.
- All nine requested reusable investigation components, including hypothesis ranks, evidence reference/detail, quality, abstention, uncertainty, timeline, status and provenance panels.
- Strict versioned runtime contracts and backend mapping; separate presentation, application hooks/workflow functions, repository interface, fixture adapter and precomputed synthetic JSON. No HTTP adapter or fabricated endpoint.
- Four deterministic cases generated from unchanged local M2 code, with 145 original synthetic observations: ranked CO₂ pattern, missing CO₂ evidence, competing fully supported patterns and simultaneous conflicts. The browser does not run inference.
- Existing Phase 1 dashboards, charts, data exploration, selectors and offline behavior remain available. The two promoted modules now have `phase2` metadata; the old route regression assertion recognizes their new implementation status.

## Source changes

New: `src/contracts/investigation.ts` and tests; `src/infrastructure/investigations.ts`; `src/infrastructure/fixtures/investigations.json`; `src/features/investigations/{application.ts,Intelligence.tsx,phase2.test.tsx}`; `src/features/incidents/{application.ts,application.test.ts,Incidents.tsx}`; `src/shared/investigation/components.tsx`; `scripts/generate_investigation_fixtures.py`; `PHASE2_CONTRACT_MAPPING.md`; this report.

Extended: `src/app/{App.tsx,modules.ts,App.test.tsx}`, `src/contracts/observation.ts`, `src/infrastructure/observations.ts`, `src/shared/ui.tsx`, `src/styles.css`, `README.md`. No dependency or lockfile changes were needed.

## Verification

- Strict TypeScript: `npm run typecheck` passed.
- Tests: `npm test` passed **68 tests / 5 files**: original 39 regression cases plus 29 Phase 2 cases.
- Formatting: `npm run format:check` passed.
- Production: `npm run build` passed. The existing two non-fatal Rollup warnings concern third-party Zod comment annotations; no application error or oversized-chunk warning occurred.
- Python fixture helper: Ruff lint/format and strict mypy passed using the existing backend tooling, scoped to that frontend script.
- Regeneration: executing the generator in memory reproduced the checked-in JSON exactly by value and asserted all four expected M2 outcomes. No backend implementation or test file was modified or executed as a test suite.
- Chrome 156 production smoke checks: `/ai-intelligence` and `/incidents` rendered with correct headings, synthetic labels and safety status at 390px and 1440px iframe widths. Document/client widths matched (375/375 and 1425/1425), with no document-level horizontal overflow. The intelligence desktop screenshot was visually inspected.
- `git diff --check` passed for tracked changes; new/extended frontend source passed Prettier. The current branch and existing backend diff summary were checked against the initial state.

Interaction tests cover selected/abstained results, ties, safety, evidence navigation and keyboard dismissal, shared crew context, complete archived windows, incident notes/status persistence across routes, acknowledgement/closure/reopening, filters, missing evidence, safe source errors/retry, empty sources and unavailable deep links. Contract tests cover unsupported versions/safety, malformed rank/numbers, unknown fields, unresolved/duplicate IDs, scope/time/provenance mismatch, null selection and quality lineage.

During verification, tests caught incorrect spacecraft scope in the first CO₂ fixture draft: M2 requires compartment scope. The generator was corrected and the original backend behavior preserved. Python helper lint/type issues were also corrected. Final applicable checks pass. No new dependency installation was necessary. There is no configured frontend ESLint command; Prettier, strict TypeScript, tests and scoped helper lint are the available checks, not a claimed ESLint pass.

## Limitations and next task

No live backend/AI integration, clinical probability, diagnosis, treatment, authentication or persistence is provided. Incident classifications are fixed demo annotations. Timeline review/evaluation times are explicitly synthetic storyboards, not engine telemetry or human audit records. Manual notes use actual session entry time and disappear on reload; do not enter personal health data.

Archived investigation windows are immutable; global time-range controls do not filter away their supporting evidence. Shared crew filters apply. Deep links incompatible with crew/status filters show unavailable state instead of another person's evidence. The supported observation subset expanded from six to nine metrics; it is still not the complete Python registry. The synthetic-only envelope requires review before any real-data integration.

Browser verification is rendering/layout smoke coverage; full browser interaction automation, screen-reader review and clinical validation were not performed. Passing software tests establishes no operational or medical suitability.

Next: review the two workspaces and approve any future local transport and persistence contracts separately. The repository interface is ready for that work, but no endpoint or safety policy is assumed. See [the mapping](PHASE2_CONTRACT_MAPPING.md) and [README](README.md).
