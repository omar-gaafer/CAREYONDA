# CAREYONDA AI implementation inventory

Audit date: 2026-11-13. Based on executable source, file sizes, and tests, not roadmap names. This synchronization publishes D2/D3 on the existing `feature/training-ready` branch and deliberately excludes the separate uncommitted M2 files. No trained model is present.

| Component | Original development workspace / implementation | Included in synchronized source |
| --- | --- | --- |
| Evidence schema / validation | Implemented: versioned observations, typed scope/measurement/provenance/quality, metric registry, safe validation wrapper, physical quality evaluation | Yes: `schemas/observation.py`, `quality/validator.py`. M2 `evidence.py` and `investigation.py` remain local only; their published placeholders are empty. |
| Synthetic mission simulator | Implemented: seeded four-scenario generator, missingness, JSON/CSV/schema/lineage export | Yes: `simulator/mission_generator.py`, `simulator/run_simulation.py` |
| Temporal features | Implemented: causal synthetic five-minute windows; separate real ISS thirty-minute windows and chronological split resets | Yes: `features/temporal_features.py`, `features/environmental.py` |
| NASA RR-1 adapters | Partially implemented: environment and daily rates executable; ambiguous accumulated units explicitly unavailable; date-only radiation timing flagged suspect | Yes: `ingestion/nasa_rr1.py`, `ingestion/nasa_rr1_export.py`. Raw files excluded. |
| Anomaly detection models | Placeholder: `ai/anomaly.py` and `ai/baseline.py` are zero-byte files | No model implementation or learned parameters |
| Model training scripts | Not implemented: no training entry point; only dataset generation/export | No model fitting, evaluation pipeline, or model artifacts |
| Hazard knowledge graph | Placeholder: `ai/knowledge_graph.py`, `knowledge/hazard_graph.yaml`, `knowledge/references.yaml` are empty | Empty scaffold only |
| Hazard reasoning engine | Implemented locally as a limited deterministic M2 prototype: reference rules, ranking, evidence and abstention; not a trained model | Excluded: uncommitted `ai/hazard_reasoning.py`, M2 schemas/tests/report are preserved locally |
| Explanation generation | Implemented locally: deterministic M2 text from structured evidence | Excluded: uncommitted `ai/explanations.py`; published file remains empty |
| Safety policy engine | Placeholder: `safety/policy_engine.py`, `safety/procedure_registry.py` are empty | No approved clinical policy or procedure implementation |
| FastAPI integration | Placeholder: `app/main.py`, API modules, core config are empty; FastAPI is not a declared dependency | No runnable HTTP server or endpoints |

`ai/probabilistic.py` and `ai/temporal_fusion.py` are also empty placeholders; existing temporal feature calculations are not a probabilistic fusion model. Architecture documents and “Model A/B” handoff names do not imply implemented or trained models.

M1.3 can begin as independent training work using existing, separate data contracts. Model frameworks, training code, evaluation, and artifacts remain to be implemented by the teammate under an approved scope. Synthetic labels are not medical diagnoses. NASA training data is unlabeled and is not certified anomaly-free. Radiation and human health data are not paired or merged.

See [TRAINING_HANDOFF.md](TRAINING_HANDOFF.md) for exact setup, dataset reproduction, feature schemas, raw-file handoff, branch boundaries, and verified test results. No redistribution permission for the supplied CSV copies was found locally, so raw data and generated datasets are excluded from this push.

**Model A update (branch `feature/omar-model-a-training`):** Model A training, evaluation, verified artifact persistence and inference are implemented in separate `app/training`, `app/ai/nasa_environment_anomaly.py`, `app/storage` and `app/schemas` modules, with synthetic-only tests. The trained artifact and NASA-derived evaluation stay in ignored local `artifacts/model_a/`. See [MODEL_A_NASA_ENVIRONMENT.md](MODEL_A_NASA_ENVIRONMENT.md). The table above still describes the shared placeholders (`ai/anomaly.py` remains empty); Model B is not implemented.

The confirmed M1.3 plan is two unsupervised Isolation Forests: Model A on real NASA RR-1 CO2/temperature/humidity features; Model B on synthetic physiological/mission-context features, with scenario labels reserved for evaluation. These are approved model definitions, not implemented training code or trained artifacts.

This dedicated training branch starts at the shared handoff `bfc19cb`. References above to local M2 describe the original development worktree only; the training worktree and published branch contain no executable M2 implementation.
