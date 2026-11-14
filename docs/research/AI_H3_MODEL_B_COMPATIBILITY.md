# AI-H3 Model B contract compatibility review

## Reviewed local snapshot

Read-only inspection of `/home/darknight90/CAREYONDA-model-b-integration` on `feature/model-b-integration`, whose committed HEAD is `1ebdd03a8b29239742074e3ac0bff247d8a5785b`. The Model B schema, inference, storage, training and associated documentation are **uncommitted/untracked work**, so HEAD does not identify this contract. No files in that worktree were modified, imported, executed or copied into this branch; no model artifacts or datasets were loaded.

Reviewed `backend/app/schemas/model_b.py` SHA-256: `4617233d984fb5f2f631ce56891b39fd8b1c48d7c0beebaa9cfdcd996275aff8`.

Reviewed `docs/research/MODEL_B_TRAINING.md` SHA-256: `dc02f20246fd359f3f2a04010f5da9ef7f25e9baa9d7e6cae3acf924f975e405`.

Also inspected the inference interface and verification/audit documentation locally. This is a static compatibility review, not a rerun or endorsement of Model B training metrics. The snapshot may change as its owner continues development.

## Contract mapping

| Concern | Local Model B contract | H1/H2 compatibility and required work |
|---|---|---|
| Scope | `source_origin=simulated`, `interpretation=synthetic_research_only`; SampleAnchor contains mission, astronaut, spacecraft, compartment, episode and sample IDs | Potentially compatible with synthetic astronaut evidence only when actual mission/subject/dataset/run identities match. “Synthetic” alone does not establish shared context. H1/H2 require explicit Scope and exact SourceRequirement identity. |
| IDs | Finding retains context, sample_id, episode_id and pooled evidence_ids; input has feature_evidence_ids and window_observation_ids | Resolve IDs to the original ResearchEvidence snapshots, preserving feature-specific lineage from input; the finding alone loses that per-feature mapping. Validate no duplicate/conflicting identities. |
| Event/availability time | Anchor timestamp is timezone-aware UTC; availability is explicitly `retrospective_event_time_not_live_arrival`; no finding assessment timestamp, per-observation arrival receipt or raw event-window envelope | Insufficient for prospective H1/H2. Require genuine source availability plus assessment time and explicit current/reference supports. Until available, preserve a retrospective-only envelope and abstain from prospective association; never synthesize arrival time from event time. |
| Features/units | Fixed versioned 16-element order: heart-rate latest/missing/mean (bpm/1/bpm); cabin CO2 partial pressure (Pa/1/Pa); sleep duration (h/1/h); fatigue latest/missing (1/1); communication delay (s/1/s); exercise latest/missing (1/1) | Metric units overlap M1/M2, but Model B vector aggregates are not raw observations. Preserve window definitions, aggregation, feature order, schema version, units and evidence support; no implicit conversion between Model A CO2 concentration ppm and pressure Pa. |
| Statistical meaning | `negative_sklearn_score_samples`, higher is more anomalous; strict score > threshold, threshold derived from a training-baseline quantile; equality is not flagged | This is a statistical anomaly score, not a probability, clinical confidence, severity, diagnosis or directional support for an M2 hypothesis. Descriptive standardized deviations are explicitly not model attribution. A cross-model association requires a separately reviewed policy, never a direct flag-to-hazard mapping. |
| Missingness/abstention | Input preserves nulls and missing indicators; finding records imputed_features; all six observed metric families absent produces abstention. Abstained finding requires null score/flag and reasons; partial missingness may be median-imputed | Preserve original nulls, imputation and reasons. Imputed values cannot become observed evidence or normality. Model abstention must remain explicit; policy-required model absence blocks association. |
| Provenance | Dataset and training manifest SHA-256, optional artifact SHA-256, model/version/policy, pooled evidence IDs | Useful but incomplete for exact source matching: need dataset/run identity, source/sensor/epoch, raw snapshots, actual availability and transformations. Hashes are identifiers, not evidence of authentication or shared scope. |
| Public inference | `IsolationForestAnomalyModel.assess(Sequence[ModelBInput]) -> tuple[ModelBFinding, ...]`; trusted artifact loading is separate | No direct H1/H2 plug-in: their current model-context input is the Model A-specific EnvironmentalAnomalyContext. Do not coerce a Model B finding into that environmental contract. |

## Adapter decision and blockers

**Not ready for direct cross-model association.** A separately authorized, reviewed research adapter and model-neutral or explicitly Model B context contract are required. That future adapter must retain the native Model B finding, original input/feature lineage, full source identity, bounded windows and genuine availability receipts; distinguish retrospective evaluation from prospective evidence; validate exact subject/mission scope; propagate abstention/imputation; and keep scores descriptive. Contract work must follow the existing layer boundaries (the inspected Model B schema currently imports SampleAnchor from the features layer and merits architecture review before publication). No adapter or contract change is implemented here.

Model A historical NASA replay remains spacecraft environmental evidence with replay acquisition semantics, while these challenge cases are synthetic astronaut behavioral evidence. A NASA/ISS label, nearby timestamp or statistically anomalous score does not supply shared subject/exposure context. No genuine shared context was established. Do not combine these records, infer exposure or substitute ppm for Pa without explicit validated inputs and reviewed transformations.

Final handoff: obtain an owner-reviewed, committed Model B contract and snapshot; agree on availability and lineage requirements; then authorize adapter-contract tests and a new independently specified cross-model challenge set. Existing Model B artifacts, NASA data, M4.2, M2, APIs and frontend remain untouched.
