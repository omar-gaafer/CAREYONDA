# Model C ↔ AI-H1/AI-H2 research compatibility review

Date: 2026-11-14. Status: **review only — no adapter is implemented.**

- **Model C:** `feature/omar-model-c`, model `careyonda-model-c-isolation-confinement` 1.1.0, method `model-c-bin-median-raw-mad-1.0.0`.
- **Contracts reviewed read-only** on `origin/feature/ai-hybrid-enhancement` at `1bd07ed`:
  - AI-H1 `TemporalSummary` / `TemporalPolicy` (`backend/app/schemas/temporal.py`);
  - AI-H2 `HybridAssessment` / `HybridPolicy` (`backend/app/schemas/hybrid.py`).
- **Branch relationship:** that branch shares the base `1ebdd03` with Model C but contains no Model C code. Nothing on it was modified.

Model C is a deterministic sleep/fatigue research monitor. It is not an isolation/confinement detector, and any adapter must preserve that.

## 1. Summary

| Level | Compatibility |
| --- | --- |
| Evidence records | **Direct.** Model C evidence is M4.2 `ResearchEvidence`, which is exactly what `TemporalSummary.supporting_evidence` and `HybridAssessment.evidence_snapshots` hold. |
| `sleep_duration` | **Possible with conditions** (§3). It is a numeric astronaut-scope metric in canonical `h`. |
| `fatigue_self_report` | **Incompatible with AI-H1.** `TemporalPolicy` calls `validate_numeric_metric`, so categorical metrics are rejected. Model C's fatigue counts have no AI-H1/H2 representation. |
| Model C result as a "model context" | **Incompatible today.** `TemporalSummary.model_contexts` and `HybridAssessment.model_contexts` accept only Model A `EnvironmentalAnomalyContext`. |
| Model C scores as AI-H1 patterns | **Not equivalent.** AI-H1 computes its own patterns (`persistent_anomaly` … `abstained`) from raw evidence. Model C raw-MAD findings must not be relabelled as patterns. |

## 2. Field-by-field mapping

| Concern | Model C 1.1.0 | AI-H1 / AI-H2 | Gap |
| --- | --- | --- | --- |
| **Scope** | `subject_id` + `mission_id`; evidence `Observation.scope` is `AstronautScope` | `TemporalPolicy.scope: Scope` (exact equality with each observation's scope); `HybridPolicy.association_mode="exact_scope_only"` | Maps directly for astronaut scope. Local manual entries use `mission_id="no-mission-declared"`, so they cannot match any M2 investigation scope, and must not be forced to. |
| **Participant identifier** | Pseudonymous `astronaut_id` (Identifier; the local entry form also restricts it to `[A-Za-z0-9_-]{3,40}`) | Same `Identifier` in `Scope` | None. |
| **Source identity** | `IndicatorSource{indicator, instrument_kind, source_id, sensor_id, sensor_epoch}` + request `dataset_id`/`run_id`/`data_origin` | `SourceRequirement{requirement_id, dataset_id, run_id, source_id, sensor_id, sensor_epoch, data_origin, compatibility, metric, unit, maximum_age_seconds}` | All identity fields map. **`instrument_kind` has no counterpart:** a self-report form's id/version would sit in `sensor_id`/`sensor_epoch` with nothing marking it as a form. An adapter must carry that distinction (for example in `TemporalPolicy.convention_reference` and limitations) or the contract needs a field. `maximum_age_seconds` must be chosen explicitly. |
| **Evidence IDs** | `AnomalyFinding.evidence_ids`, `profile_lineage_ids`, baseline `included`/`excluded`; categorical `reference_report_ids`/`assessment_report_ids`; `unused_evidence_ids` | `TemporalSummary.observation_ids` (ordered, must equal supporting evidence), `excluded_evidence`, `missing_or_unavailable`; `HybridAssessment.supporting/contradicting_evidence_ids`, `missing_evidence` | Observation IDs carry over unchanged. AI-H1 additionally requires **distinct, ordered event times** across supporting evidence. Model C excludes conflicting simultaneous readings but allows identical duplicates at one timestamp, so an adapter must de-duplicate or exclude them. |
| **Provenance** | Full `Observation.provenance` (origin, source type, simulation metadata) inside each `ResearchEvidence`; `evidence_provenance` summary; `data_origin` | Same embedded `ResearchEvidence`; mixed real/synthetic prohibited by fusion rules | Preserved. Local entries are `real` + `self_reported`; current M2/AI-H examples are synthetic. They cannot be combined. |
| **Event time** | `Observation.timestamp` (UTC); `temporal_support` interval (sleep: (D−1 12:00, D 12:00]; fatigue: point) | `TemporalPolicy.event_window` (start, end]; each support must satisfy `start < support.start ≤ support.end ≤ end` | Same half-open convention, now enforced on Model C targets as well (since `5b741bb`). |
| **Availability time** | `Observation.ingested_at`; `ModelCParameters.availability_mode` = `retrospective` (default) or `prospective` | **Prospective is mandatory** (`available_at(..., "prospective")` for every supporting record) | Retrospective Model C runs must not be fed to AI-H1 as if available. Local entries set `ingested_at` = server receipt time, so they qualify only when assessed at or after receipt. |
| **Assessment time** | `assessed_at` (UTC) | `TemporalSummary.assessed_at ≥ event_window.end`; `HybridAssessment` quarantines future summaries | Compatible. |
| **Model / method version** | `model_id`, `model_version` 1.1.0, `method_version`, `schema_version` 1.0.0, `interpretation="research_only"` | `TemporalSummary.method_version="temporal-evidence-1.0.0"`; `HybridAssessment.method_version="hybrid-evidence-1.0.0"`; model provenance only via `EnvironmentalAnomalyContext.model` | **No field records a Model C model/method version.** Supplying evidence alone would drop the fact that Model C selected it. A contract extension or a sidecar is required to keep it. |
| **Statistical reference** | Personal baseline median and raw MAD (bin medians), status `ready` / `flat_reference` / `insufficient_reference` / `unsupported` | `TemporalPolicy.reference_lower` / `reference_upper` (finite bounds) + `convention_reference` | Model C provides no bounds. Deriving them (for example median ± k·MAD) would introduce a new threshold. That requires an explicitly reviewed research convention, which Model C does not have (its thresholds are `unassessed` by default). |

## 3. Status semantics

| Model C | Meaning | Nearest AI-H concept | Rule for a future adapter |
| --- | --- | --- | --- |
| Finding `scored` | Raw-MAD distance computed against a `ready` personal baseline; **not** a probability, z-score or flag | None. AI-H1 does not consume external scores. | Pass the underlying evidence only. Never pass the score as a pattern or flag. |
| `threshold_status="unassessed"` (default) | No approved research threshold, so no decision | AI-H1 has no threshold decision; AI-H2 statuses are descriptive | Must stay "no decision". It must not become `supports`/`contradicts`. |
| `threshold_status` `exceeded` / `not_exceeded` | Only with an `approved_research` policy | None | Out of scope until an approved threshold and an AI-H rule reference it. |
| Finding `flat_reference` / `insufficient_reference` / `unsupported` / `invalid_observation` | Abstention with reason codes | AI-H1 `pattern="abstained"` + `abstention_reasons`; AI-H2 `insufficient_evidence` / `incompatible_evidence` | Map to abstention with reasons preserved verbatim. |
| Indicator / overall `abstained`, `partially_assessed` | Per-indicator abstention; never combined | AI-H2 `missing_evidence` / `abstention_reasons` | Each indicator separately. Never aggregate into one status. |
| Categorical fatigue counts | Descriptive self-report counts, no score | None | Not representable. Exclude with an explicit `unsupported_categorical_metric` reason. |

## 4. Requirements for a future research adapter (not implemented)

1. **Read-only and one-directional:** Model C request → `ResearchEvidence` → AI-H1 `analyze_temporal_evidence`. Do not modify AI-H1/H2, M2 or Model C contracts within the adapter.
2. **`sleep_duration` only.** Fatigue is reported as unsupported, never coerced to numbers.
3. **Prospective availability only.** Reject or exclude records whose `ingested_at` is missing or later than the assessment time.
4. **Exact scope and source.** Build `Scope` and `SourceRequirement` from the Model C request. Refuse records with mismatched mission/subject, mixed origins, or the `no-mission-declared` placeholder when joining M2.
5. **Make `instrument_kind` explicit.** Either an AI-H contract field, or a documented convention plus limitation, so form identities are never read as device identities.
6. **No invented bounds.** `reference_lower`/`reference_upper` need a reviewed convention with a citation. Until then the adapter must abstain.
7. **Preserve Model C provenance:** model id/version, method version, baseline `profile_id` and parameters, carried in a versioned sidecar or contract field.
8. **Event times:** distinct, strictly ordered event times for supporting evidence. Duplicates are excluded with reasons.
9. **Semantics:** keep abstentions and reason codes verbatim. Scored Model C findings never become AI-H outcomes.
10. **Tests:** synthetic-only round trips covering scope mismatch, retrospective-only data, categorical exclusion, duplicate timestamps, missing bounds, and the absence of any probability or diagnostic field.

## 5. Not established

None of these contracts, or their combination, validates clinical relevance, isolation/confinement effects, causal links between sleep/fatigue and hazards, or operational suitability.
