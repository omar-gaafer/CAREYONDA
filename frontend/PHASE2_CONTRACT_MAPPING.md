# Phase 2 — backend contract mapping

> Historical research behavior. The production entry is now API-only; see
> [FRONTEND_DATA_AUDIT.md](FRONTEND_DATA_AUDIT.md). Fixture workflows remain test-only.

Audited local sources: `backend/app/schemas/{observation,evidence,investigation}.py`, `ai/{hazard_reasoning,explanations}.py`, `features/temporal_features.py`, `quality/validator.py`, M2 unit/integration tests, and `docs/architecture/M2_HAZARD_REASONING.md`. These files remain unchanged. Historical implementation reports are not API specifications. HTTP modules remain placeholders; no endpoint is assumed.

## Wire representation

| Backend contract                 | Frontend boundary                                | Mapping                                                                                                                                                            |
| -------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Observation`, version `1.0.0`   | `observationSchema`, `Observation`               | Original ID, domain/metric, discriminated scope and measurement, timezone-aware event/ingestion timestamps, quality and provenance                                 |
| `EvidenceFinding`                | `evidenceFindingSchema`, `EvidenceFinding`       | `metric`, relation enum, current/reference ID arrays, nullable observed value/reference bounds, unit, explanation                                                  |
| `EvidenceQualityIssue`           | `evidenceQualityIssueSchema`                     | Current/reference window tag, observation ID, metric, quality status, reason codes                                                                                 |
| `HypothesisResult`               | `hypothesisSchema`                               | Hypothesis ID, positive integer rank, compatibility enum, expected relations, three evidence groups, explanation and uncertainty strings                           |
| `Investigation`, version `1.0.0` | `investigationSchema`, `Investigation`           | All result fields retained; engine version is exactly `reference-rules-1.0.0`; safety is exactly `not_evaluated`                                                   |
| `SampleAnchor`                   | Private `anchorSchema` in investigation boundary | Sample/episode/mission/astronaut/spacecraft/compartment IDs and timezone-aware timestamp                                                                           |
| No backend envelope              | `investigationCaseSchema`, `InvestigationCase`   | Frontend-only `fixture_version=1.0.0`, `origin=synthetic_precomputed`, display title, current/reference anchors, original observations, nested unchanged M2 result |
| No backend incident model        | `IncidentReview`, `reviewIncident`               | Separate, in-memory human workflow: open/acknowledged/closed and manual session notes. Does not mutate results or imply medical resolution                         |

JSON encodes Python tuples as arrays and `None` as null. Strict objects reject unknown fields. Defaults match the M2 result/evidence schema for versions, safety status, optional finding arrays and nullable values. Supplied unsupported versions, safety values, non-finite numeric values and malformed timestamps fail validation. The browser accepts timezone-aware ISO strings; it does not reproduce Pydantic's other Python input coercions. UTC formatting normalizes display only.

The observation boundary now supports nine metrics: the original six numeric metrics plus numeric communication delay (`s`), boolean exercise state, and categorical fatigue (`rested`, `tired`, `very_tired`). These are supported backend variants, not invented health measurements. Other backend metric identifiers still fail explicitly. Units are never implicitly converted. Numeric quality is preserved; schema validation is distinct from `evaluate_quality`, which may mark a physically invalid raw reading as evaluated-invalid without changing the source record.

## Windows, scope and lineage

M2 results have anchor endpoints and a shared positive `window_seconds`, not nested window objects. UI boundaries are derived as `(timestamp-window_seconds, timestamp]` independently for current and reference. The earlier reference must end no later than the exclusive current lower boundary. Reference means empirical comparator, never assumed healthy or personalized.

M2 `build_features` selects exact mission/astronaut context, CO₂ partial pressure from the selected **compartment**, and communication delay from the selected spacecraft. Fixture generation uses those actual scope rules. Feature windows are retrospective event-time windows: late-arriving evidence can be included, so these are not online-availability replays.

The frontend envelope additionally checks anchor/result agreement, unique evidence/result/hypothesis IDs, reference chronology, synthetic origin, window membership, subject/location context, resolved lineage, finding references inside their respective windows, quality-issue references, and selection/abstention/conflict consistency. These are integration integrity checks beyond standalone Pydantic field validation. They do not recompute rankings, validate source authenticity, or establish reference appropriateness.

## Ranking and abstention

- Hypothesis IDs: `baseline`, `elevated_co2`, `sleep_deprivation`, `recent_exercise`.
- Compatibility: `supported`, `partial`, `mixed`, `contradicted`, `insufficient`.
- Engine order: compatibility category, fewer contradictions, fewer missing findings, then more supporting findings. Substantive ties share competition rank. Hypothesis ID stabilizes display only.
- `ranked`: exactly one fully supported pattern selected.
- `ambiguous`: multiple fully supported patterns; no selection.
- `insufficient_evidence`: no fully supported pattern; no selection. This can describe mixed/contradicted patterns as well as missing inputs.
- `conflicting_evidence`: simultaneous conflicting evidence; no selection, even if another pattern has support.

The UI renders supplied ranks and explanations without implementing ranking logic or changing ties. `baseline` is only a synthetic pattern identifier. Rank, compatibility and evidence counts are not probability, confidence, clinical severity, diagnosis or proof of causation. `safety_status=not_evaluated` is retained on every path. Closing an incident never changes it.

## Fixture generation and future integration

`frontend/scripts/generate_investigation_fixtures.py` constructs Pydantic-validated synthetic observations/anchors and calls the unchanged local `investigate` function at development time. It asserts four expected output modes and emits the actual serialized results. The fixture generator is independent of the Python mission simulator and writes only frontend JSON. No original datasets or simulator files are read or changed.

From repository root, with the existing backend environment provisioned:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python frontend/scripts/generate_investigation_fixtures.py
cd frontend
npm run format
```

Fixed mission: ARES-07, HABITAT-01/LAB-01; current endpoint 2026-11-13 11:55 UTC, reference endpoint 11:40 UTC, five-minute windows, three synthetic timestamps per window. Four cases contain 145 original synthetic observations in total. There are no clinical limits or model fits. Browser runtime only reads the bundled JSON through `InvestigationRepository.list(): Promise<unknown>` and validates it. No Python runs in the browser and no HTTP adapter is implemented.

Future adapters can implement the repository interface once real, approved contracts exist. The current synthetic-only envelope must not label real evidence synthetic; introduce an explicitly reviewed production envelope before connecting measured data. Malformed/unsupported payloads display safe errors and retry, not fabricated fallback results. Empty source, unavailable deep link, and missing evidence are different states.

Incident IDs derive from investigation IDs. Severity `review exercise` and category `synthetic evidence review` are fixed demo annotations, not inferred clinical labels. Manual notes are plain React text, bounded to 2,000 characters, with actual session-entry UTC times. Timeline creation/review/evaluation timestamps are deterministic storyboard annotations explicitly labeled synthetic; they are not recorded human actions or actual engine timing.
