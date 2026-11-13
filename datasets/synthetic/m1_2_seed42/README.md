# CAREYONDA synthetic training dataset

Toy scenarios only; labels are generator assignments, not validated diagnoses. All exposure-response effects are assumptions documented in docs/architecture/M1.2_TRAINING_PIPELINE.md. No medical thresholds are used.

Train using only feature_schema.json feature columns from features.csv; drop sample_id. Join labels.csv by sample_id for the synthetic_scenario target. Never use IDs, evidence, provenance, context, manifest, or labels as predictors. Fatigue codes: rested=0, tired=1, very_tired=2 (synthetic ordinal encoding); exercise: false=0, true=1. Empty cells are missing, not zero. Fit any imputation/scaling on the training partition only.

Windows use (t-window,t] event time, never future observations. Late-arriving evidence is included retrospectively; this is not an online arrival-time replay. Only evaluated-valid values contribute; source limitations remain in observations.json. evidence_mapping.json maps every feature to its input IDs and carries episode/time/scope context.

Split by whole episode_id from evidence_mapping.json, preferably hold out a separate seed. Do not randomly split overlapping rows; they share evidence and synthetic episode effects. Each episode has one fixed scenario, known at its first sample. This dataset supports current-scenario classification, not forecasting or causal inference.

{
  "config": {
    "baseline_co2_pa": 50.0,
    "baseline_heart_rate": 72.0,
    "baseline_sleep_hours": 8.0,
    "co2_heart_rate_increase": 18.0,
    "co2_increase_pa": 120.0,
    "communication_delay_seconds": 2.0,
    "deprived_sleep_hours": 3.0,
    "episodes_per_scenario": 8,
    "exercise_decay_minutes": 15.0,
    "exercise_heart_rate_increase": 45.0,
    "max_ingestion_delay_seconds": 120,
    "missing_probability": 0.03,
    "noise_scale": 1.0,
    "seed": 42,
    "start": "2026-11-13T00:00:00Z",
    "step_seconds": 60,
    "steps": 30
  },
  "dataset_version": "1.0.0",
  "features": 16,
  "observations": 5760,
  "quality_balance": {
    "missing": 148,
    "valid": 5612
  },
  "samples": 960,
  "scenario_balance": {
    "baseline": 240,
    "elevated_co2": 240,
    "recent_exercise": 240,
    "sleep_deprivation": 240
  },
  "synthetic_only": true,
  "window_seconds": 300
}
