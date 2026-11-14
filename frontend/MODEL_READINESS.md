# Model and backend integration readiness

Reviewed 2026-11-14. Current main workspace is `feature/hazard-reasoning`;
Model A worktree is separate. No research inference was added or executed by this audit.

| Component | Verified source implementation / location | Inputs and evidence requirements | Output/version | Availability and limitations | Frontend integration needs |
| --- | --- | --- | --- | --- | --- |
| M2 deterministic reasoning | Current `backend/app/ai/hazard_reasoning.py`, `explanations.py`; actual POST route in `api/routes.py` | Configured synthetic current/reference SampleAnchors and original observations; separate earlier reference; event windows `(t-window,t]`; scope/quality checks | Investigation schema 1.0.0; engine `reference-rules-1.0.0`; ranks/compatibility/evidence/uncertainty; safety `not_evaluated` | Executable deterministic research rules; capability `simulation_only`. No model probabilities, clinical calibration or safe-state guarantee. Retrospective event time does not establish online availability | Existing synthetic transport and result validators retained/tested in isolated harness. Production remains disabled pending separately reviewed authorized source/context contracts; never invent incidents from M2 |
| Model A environmental anomaly | Separate accessible `CAREYONDA-model-a-integration`: `ai/nasa_environment_anomaly.py`, `application/environmental_anomaly.py`, `environmental_api.py`, `storage/nasa_environment_model_store.py`, optional `model_a_main.py` | Trusted local artifact/pinned runtime; NASA-RR1/ISS canonical 16-feature stream; original observation history; increasing unique times; explicit availability/ingestion; server-authorized catalog and factual live/replay acquisition receipts | EnvironmentalAnomalyContext sidecar schema/model compatibility 1.1.0; model feature schema 1.0.0; versioned manifest/artifact identity, score, threshold/method, imputation/abstention and evidence lineage | Implemented optional code and separate GET `/api/v1/environmental/authorized-samples` / POST `/api/v1/environmental/anomaly-context` source exist in that worktree, **absent from current API**. Unconfigured model/catalog is unavailable. Fitted artifact execution was not independently verified here; checkpoint presence is not availability | Separate integration review/deployment, capability discovery/version contract, trusted artifact/runtime and authorized catalog/receipts, source-specific nonclinical display. Do not copy its simulated panel or fixture into this production bundle |
| Baseline research | Current `schemas/baseline.py` implemented; `ai/baseline.py` zero bytes | Explicit dataset/run/mission/subject/source/sensor epoch; canonical numeric unit; reference bins/coverage/span/gap/freshness/availability policy; included/excluded provenance | BaselinePolicy/BaselineProfile research schema 1.0.0; ready/unsupported/insufficient_reference/flat_reference | Contracts only; no estimation algorithm, API, reference artifact or clinical personal baseline | Future separately approved estimator and application/transport contract; preserve zero MAD and abstention, never infer normality |
| Raw-MAD anomaly research | Current `schemas/anomaly.py` implemented; `ai/anomaly.py` zero bytes | Validated profile + original target; compatible identity/unit; explicit governance/calibration/approval if a research threshold decision is intended | AnomalyPolicy/AnomalyFinding 1.0.0; nullable raw-MAD statistical deviation and threshold status | Contracts only; no scorer, calibration artifact or endpoint. Score is not probability/severity/risk. No epsilon substitution for zero MAD | Future endpoint and policy/artifact/evidence provenance; render supplied values and abstention only |
| Temporal fusion | Current `schemas/fusion.py` implemented; `ai/temporal_fusion.py` zero bytes | Explicit event window/source ages/separation, exact context, documented subject-compartment association, origin/unit/quality/availability; original evidence | FusionPolicy/TemporalEvidenceGroup 1.0.0; aligned/no_data/insufficient/conflicting/unsupported | Contracts only, no temporal join/inference API. No NASA-to-synthetic physiology association or causality inferred | Separately authorized selector and transport; display full temporal support and unsupported/missing/conflicting evidence |
| Probabilistic / knowledge graph | Current `ai/probabilistic.py`, `ai/knowledge_graph.py` zero bytes; no implemented graph query/inference contract | No approved graph/model/artifact or probability calibration | No operational output schema | Unimplemented; no probabilities or causal explanations supplied | Define reviewed domain contracts and independently validate model before exposing results |
| Explanations | Current M2 deterministic text from supplied structured evidence; Model A separate worktree has fixed scientific limitations | Original evidence IDs, current/reference time/context and model/method version | M2 explanations and uncertainty inside Investigation; Model A sidecar fields only in separate worktree | No grounded assistant endpoint or generated medical advice | Preserve original text, rank semantics, evidence and safety; do not simulate a chat response |
| Evaluation outputs | Synthetic deterministic software tests and separate Model A integration documentation exist | Approved evaluation dataset/provenance/splits and versioned artifacts not exposed through current API | No versioned retrieval endpoint for validation reports or calibration | Passing tests and branch/checkpoint existence do not establish measured/clinical model validation | Dedicated reviewed read-only evaluation contract before presenting performance or confidence |

## Remaining backend blockers

1. **Authentication and authorization:** current capability schema declares
   `none_local_only`. No real-person health records may be accessed through this UI.
   Need authorized subject/mission/location context and reviewed error/access policy.
2. **Measured observation transport:** current ObservationPage/Contexts v1 source is
   exactly `configured_synthetic`; current composition rejects non-simulated records.
   Do not expand frontend enums to bypass it. Need explicit versioned provenance,
   availability/freshness and source-authorization contract, including pagination
   consistency. Current frontend observation metric subset is not the full backend
   registry; new metrics need explicit validation review.
3. **Mission overview/context:** no launch/mission elapsed time, status or authorized
   crew catalog endpoint. No dashboard can infer them from observation IDs.
4. **Model A deployment:** separate worktree review and controlled integration,
   compatible dependency/artifact identity, approved sample catalog and factual
   acquisition receipts; extend capability metadata explicitly. No import/merge or
   actual artifact assessment was authorized by this task.
5. **Other AI milestones:** baseline/scoring/fusion algorithms remain unimplemented;
   M4.2 contracts are not executable research models. Need separate milestones,
   scientific evaluation and application/HTTP contracts.
6. **Operational incidents/assistant:** no incident lifecycle, alert policy, or grounded
   assistant endpoint. Do not treat compatible hypotheses as incidents/diagnoses.
7. **Recommendations:** no approved versioned procedure source or independent safety
   engine; actionable treatment or flight commands remain disabled.
8. **Digital twin:** no trustworthy static geometry or live sensor/context schema.
9. **Reports/history:** no saved investigation retrieval, historical archive/replay or
   report-generation contract. Only an in-memory synthetic research test workflow
   previously existed; no operational history is fabricated.
10. **Sources/science:** NASA redistribution permissions, radiation timing/units,
    original ingestion availability and unpaired physiology remain explicit limits;
    never use synthetic crew or invented acquisition times to fill gaps.

Current production gating intentionally stays closed even if an existing component's
capability changes from simulation_only to available: that does not authorize a new
source envelope, authentication mode or real health access. A separately reviewed
backend/frontend contract change must implement those boundaries together.
