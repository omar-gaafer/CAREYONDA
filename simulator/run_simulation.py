"""CLI and artifact export for the synthetic training MVP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.features.temporal_features import build_features, feature_schema
from simulator.mission_generator import (
    SimulationConfig,
    SyntheticMission,
    generate_mission,
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_dataset(
    mission: SyntheticMission, output: Path, window_seconds: int = 300
) -> dict[str, object]:
    samples = build_features(mission.observations, mission.anchors, window_seconds)
    if set(mission.labels) != {sample.anchor.sample_id for sample in samples}:
        raise ValueError("labels and sample IDs must match exactly")
    if not samples:
        raise ValueError("cannot export an empty dataset")
    # Refuse existing destinations; never delete or overwrite a teammate's dataset.
    output.mkdir(parents=True, exist_ok=False)
    columns = list(samples[0].values)
    with (output / "features.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", *columns])
        writer.writeheader()
        for sample in samples:
            writer.writerow({"sample_id": sample.anchor.sample_id, **sample.values})
    with (output / "labels.csv").open("w", newline="", encoding="utf-8") as handle:
        label_writer = csv.writer(handle)
        label_writer.writerow(["sample_id", "synthetic_scenario"])
        label_writer.writerows(
            (s.anchor.sample_id, mission.labels[s.anchor.sample_id]) for s in samples
        )
    _write_json(
        output / "observations.json",
        [o.model_dump(mode="json") for o in mission.observations],
    )
    _write_json(output / "feature_schema.json", feature_schema(window_seconds))
    _write_json(
        output / "evidence_mapping.json",
        [
            {
                "sample_id": s.anchor.sample_id,
                "context": s.anchor.model_dump(mode="json"),
                "feature_observation_ids": s.evidence,
                "window_observation_ids": s.window_observation_ids,
            }
            for s in samples
        ],
    )
    manifest: dict[str, object] = {
        "dataset_version": "1.0.0",
        "synthetic_only": True,
        "config": mission.config.model_dump(mode="json"),
        "window_seconds": window_seconds,
        "observations": len(mission.observations),
        "samples": len(samples),
        "features": len(columns),
        "scenario_balance": dict(sorted(Counter(mission.labels.values()).items())),
        "quality_balance": dict(
            sorted(Counter(o.quality.status for o in mission.observations).items())
        ),
    }
    (output / "README.md").write_text(
        "# CAREYONDA synthetic training dataset\n\n"
        "Toy scenarios only; labels are generator assignments, not validated diagnoses. "
        "All exposure-response effects are assumptions documented in "
        "docs/architecture/M1.2_TRAINING_PIPELINE.md. No medical thresholds are used.\n\n"
        "Train using only feature_schema.json feature columns from features.csv; drop sample_id. "
        "Join labels.csv by sample_id for the synthetic_scenario target. "
        "Never use IDs, evidence, provenance, context, manifest, or labels as predictors. "
        "Fatigue codes: rested=0, tired=1, very_tired=2 (synthetic ordinal encoding); "
        "exercise: false=0, true=1. Empty cells are missing, not zero. "
        "Fit any imputation/scaling on the training partition only.\n\n"
        "Windows use (t-window,t] event time, never future observations. "
        "Late-arriving evidence is included retrospectively; this is not an online arrival-time replay. "
        "Only evaluated-valid values contribute; source limitations remain in observations.json. "
        "evidence_mapping.json maps every feature to its input IDs and carries episode/time/scope context.\n\n"
        "Split by whole episode_id from evidence_mapping.json, preferably hold out a separate seed. "
        "Do not randomly split overlapping rows; they share evidence and synthetic episode effects. "
        "Each episode has one fixed scenario, known at its first sample. "
        "This dataset supports current-scenario classification, not forecasting or causal inference.\n\n"
        + json.dumps(manifest, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    manifest["sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.iterdir())
        if p.is_file()
    }
    _write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New output directory"
    )
    parser.add_argument("--config", type=Path, help="Optional JSON SimulationConfig")
    parser.add_argument("--seed", type=int, help="Override config seed")
    parser.add_argument("--episodes-per-scenario", type=int)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--missing-probability", type=float)
    parser.add_argument("--window-seconds", type=int, default=300)
    args = parser.parse_args()
    config = (
        SimulationConfig.model_validate_json(args.config.read_text())
        if args.config
        else SimulationConfig()
    )
    changes = config.model_dump()
    for name in ("seed", "episodes_per_scenario", "steps", "missing_probability"):
        value = getattr(args, name)
        if value is not None:
            changes[name] = value
    config = SimulationConfig.model_validate(changes)
    summary = export_dataset(generate_mission(config), args.output, args.window_seconds)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
