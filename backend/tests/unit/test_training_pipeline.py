"""Offline, synthetic-only simulator and causal export regression tests."""

import csv
import json
from collections import Counter
from datetime import UTC, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.features.temporal_features import (
    FEATURE_METRICS,
    build_features,
    feature_schema,
)
from app.quality.validator import evaluate_quality
from app.schemas.observation import METRIC_REGISTRY, Observation
from simulator.mission_generator import (
    SCENARIOS,
    SimulationConfig,
    generate_mission,
)
from simulator.run_simulation import export_dataset


def small_config(seed: int = 42, missing: float = 0.0) -> SimulationConfig:
    return SimulationConfig(
        seed=seed, steps=3, episodes_per_scenario=1, missing_probability=missing
    )


def test_seed_reproducibility_and_variation() -> None:
    first = generate_mission(small_config())
    assert first.model_dump_json() == generate_mission(small_config()).model_dump_json()
    assert (
        first.model_dump_json() != generate_mission(small_config(43)).model_dump_json()
    )


def test_scenarios_balance_schema_and_utc() -> None:
    mission = generate_mission(small_config())
    assert len(mission.observations) == 4 * 3 * 6
    assert Counter(mission.labels.values()) == dict.fromkeys(SCENARIOS, 3)
    assert len({o.observation_id for o in mission.observations}) == len(
        mission.observations
    )
    assert list(mission.observations) == sorted(
        mission.observations, key=lambda o: (o.timestamp, o.observation_id)
    )
    for record in mission.observations:
        assert record.timestamp.tzinfo == UTC
        assert record.ingested_at is not None and record.ingested_at >= record.timestamp
        assert Observation.model_validate_json(record.model_dump_json()) == record
        assert evaluate_quality(record).status == "valid"
        assert record.provenance.origin == "simulated"
        assert record.provenance.simulation is not None
        assert record.provenance.simulation.scenario_id in SCENARIOS


def test_preserves_starter_registry() -> None:
    starter_metrics = {
        "heart_rate",
        "ambient_pressure",
        "absorbed_dose",
        "sleep_state",
        "gravity_magnitude",
        "exercise_active",
        "cabin_co2_partial_pressure",
        "sleep_duration",
        "fatigue_self_report",
        "communication_delay",
    }
    assert starter_metrics <= set(METRIC_REGISTRY)


@pytest.mark.parametrize(
    "metric",
    [
        "cabin_co2_partial_pressure",
        "sleep_duration",
        "fatigue_self_report",
        "communication_delay",
    ],
)
def test_added_metric_rejects_wrong_domain(metric: str) -> None:
    record = next(
        o for o in generate_mission(small_config()).observations if o.metric == metric
    )
    data = record.model_dump()
    data["domain"] = "radiation"
    with pytest.raises(ValidationError):
        Observation.model_validate(data)


@pytest.mark.parametrize(
    "metric", ["cabin_co2_partial_pressure", "sleep_duration", "communication_delay"]
)
def test_added_units_and_physical_bounds(metric: str) -> None:
    record = next(
        o for o in generate_mission(small_config()).observations if o.metric == metric
    )
    data = record.model_dump()
    data["measurement"] = {
        "kind": "numeric",
        "value": -1.0,
        "unit": METRIC_REGISTRY[metric].canonical_unit,
    }
    assert evaluate_quality(Observation.model_validate(data)).status == "invalid"
    data["measurement"]["unit"] = "Gy"
    with pytest.raises(ValidationError):
        Observation.model_validate(data)


def test_scenario_effects_are_configurable_assumptions() -> None:
    config = SimulationConfig(
        steps=1, episodes_per_scenario=1, noise_scale=0, missing_probability=0
    )
    mission = generate_mission(config)
    rows = build_features(mission.observations, mission.anchors)
    by_scenario = {mission.labels[r.anchor.sample_id]: r.values for r in rows}
    assert (
        by_scenario["elevated_co2"]["cabin_co2_partial_pressure_latest"]
        == config.baseline_co2_pa + config.co2_increase_pa
    )
    assert (
        by_scenario["elevated_co2"]["heart_rate_latest"]
        == config.baseline_heart_rate + config.co2_heart_rate_increase
    )
    assert (
        by_scenario["sleep_deprivation"]["sleep_duration_latest"]
        == config.deprived_sleep_hours
    )
    assert (
        by_scenario["recent_exercise"]["heart_rate_latest"]
        == config.baseline_heart_rate + config.exercise_heart_rate_increase
    )
    assert by_scenario["recent_exercise"]["exercise_active_latest"] == 1
    assert by_scenario["baseline"]["exercise_active_latest"] == 0


def test_no_future_or_ingestion_order_leakage() -> None:
    mission = generate_mission(small_config())
    anchor = mission.anchors[0]
    past = tuple(o for o in mission.observations if o.timestamp <= anchor.timestamp)
    expected = build_features(past, [anchor])
    assert expected == build_features(mission.observations, [anchor])
    delayed = tuple(
        Observation.model_validate(
            {
                **o.model_dump(),
                "ingested_at": o.timestamp + timedelta(days=1, seconds=i),
            }
        )
        for i, o in enumerate(reversed(mission.observations))
    )
    assert expected == build_features(delayed, [anchor])
    for sample in build_features(mission.observations, mission.anchors):
        lookup = {o.observation_id: o for o in mission.observations}
        assert all(
            lookup[oid].timestamp <= sample.anchor.timestamp
            for oid in sample.window_observation_ids
        )
        assert all(
            lookup[oid].scope.mission_id == sample.anchor.mission_id
            for oid in sample.window_observation_ids
        )


def test_window_boundary_is_open_left_closed_right() -> None:
    mission = generate_mission(small_config())
    latest = mission.anchors[-1]
    sample = build_features(mission.observations, [latest], window_seconds=120)[0]
    lookup = {o.observation_id: o for o in mission.observations}
    assert len(sample.window_observation_ids) == 12
    assert all(
        latest.timestamp - timedelta(seconds=120)
        < lookup[oid].timestamp
        <= latest.timestamp
        for oid in sample.window_observation_ids
    )
    assert len(sample.evidence["heart_rate_mean"]) == 2


def test_missing_records_and_completely_absent_metric() -> None:
    mission = generate_mission(small_config(missing=1.0))
    assert all(o.quality.status == "missing" for o in mission.observations)
    for sample in build_features(mission.observations, mission.anchors):
        for name, value in sample.values.items():
            assert value == (1.0 if name.endswith("_missing") else None)
    present = generate_mission(small_config())
    no_hr = tuple(o for o in present.observations if o.metric != "heart_rate")
    for sample in build_features(no_hr, present.anchors):
        assert sample.values["heart_rate_latest"] is None
        assert sample.values["heart_rate_missing"] == 1
        assert sample.evidence["heart_rate_mean"] == ()


@pytest.mark.parametrize("status", ["suspect", "invalid"])
def test_questionable_data_stays_in_evidence_not_values(status: str) -> None:
    mission = generate_mission(small_config())
    anchor = mission.anchors[0]
    source = next(
        o
        for o in mission.observations
        if o.scope.mission_id == anchor.mission_id
        and o.metric == "heart_rate"
        and o.timestamp == anchor.timestamp
    )
    changed = Observation.model_validate(
        {
            **source.model_dump(),
            "quality": {"status": status, "reason_codes": ["synthetic_fault"]},
        }
    )
    sample = build_features([changed], [anchor])[0]
    assert sample.values["heart_rate_latest"] is None
    assert sample.window_observation_ids == (source.observation_id,)
    assert sample.evidence["heart_rate_missing"] == (source.observation_id,)


def test_out_of_physical_domain_excluded() -> None:
    mission = generate_mission(small_config())
    source = next(o for o in mission.observations if o.metric == "heart_rate")
    anchor = next(
        a
        for a in mission.anchors
        if a.mission_id == source.scope.mission_id and a.timestamp == source.timestamp
    )
    changed = Observation.model_validate(
        {
            **source.model_dump(),
            "measurement": {"kind": "numeric", "value": -1, "unit": "bpm"},
        }
    )
    assert build_features([changed], [anchor])[0].values["heart_rate_latest"] is None


def test_export_consistency_no_labels_and_deterministic_files(tmp_path: Path) -> None:
    mission = generate_mission(small_config())
    first, second = tmp_path / "first", tmp_path / "second"
    manifest = export_dataset(mission, first)
    export_dataset(mission, second)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    with (first / "features.csv").open() as handle:
        features = list(csv.DictReader(handle))
    with (first / "labels.csv").open() as handle:
        labels = list(csv.DictReader(handle))
    mapping = json.loads((first / "evidence_mapping.json").read_text())
    schema = json.loads((first / "feature_schema.json").read_text())
    evidence = json.loads((first / "observations.json").read_text())
    ids = {r["sample_id"] for r in features}
    assert ids == {r["sample_id"] for r in labels} == {r["sample_id"] for r in mapping}
    assert len(ids) == len(features) == 12
    names = [f["name"] for f in schema["features"]]
    assert list(features[0]) == ["sample_id", *names]
    assert len(names) == manifest["features"] == 16
    assert not set(names) & {
        "scenario",
        "label",
        "target",
        "timestamp",
        "episode_id",
        "seed",
        "synthetic_scenario",
    }
    assert all(
        not any(label in cell for label in SCENARIOS)
        for row in features
        for cell in row.values()
    )
    lookup = {o["observation_id"]: Observation.model_validate(o) for o in evidence}
    for item in mapping:
        for name, evidence_ids in item["feature_observation_ids"].items():
            assert name in names
            assert set(evidence_ids) <= set(item["window_observation_ids"])
        assert set(item["window_observation_ids"]) <= lookup.keys()
    with pytest.raises(FileExistsError):
        export_dataset(mission, first)


def test_schema_encodings_and_nullable_features() -> None:
    schema = feature_schema(300)
    assert schema["categorical_encoding"] == {
        "fatigue_self_report": {"rested": 0.0, "tired": 1.0, "very_tired": 2.0}
    }
    assert len(FEATURE_METRICS) == 6


@pytest.mark.parametrize("window", [0, -1])
def test_invalid_window(window: int) -> None:
    with pytest.raises(ValueError):
        feature_schema(window)


@pytest.mark.parametrize(
    "changes",
    [
        {"seed": -1},
        {"steps": 0},
        {"missing_probability": 1.1},
        {"noise_scale": float("nan")},
        {"start": "2026-11-13T00:00:00"},
        {"step_seconds": 0},
    ],
)
def test_invalid_config(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(changes)


def test_wrong_astronaut_and_compartment_are_not_merged() -> None:
    mission = generate_mission(small_config())
    anchor = mission.anchors[0]
    sources = [
        o
        for o in mission.observations
        if o.scope.mission_id == anchor.mission_id and o.timestamp == anchor.timestamp
    ]
    changed: list[Observation] = []
    for source in sources:
        data = source.model_dump()
        if source.scope.kind == "astronaut":
            data["scope"]["astronaut_id"] = "other-crew"
        elif source.scope.kind == "compartment":
            data["scope"]["compartment_id"] = "other-cabin"
        elif source.scope.kind == "spacecraft":
            data["scope"]["spacecraft_id"] = "other-ship"
        changed.append(Observation.model_validate(data))
    sample = build_features(changed, [anchor])[0]
    assert sample.window_observation_ids == ()
    assert all(
        value == (1.0 if name.endswith("_missing") else None)
        for name, value in sample.values.items()
    )


def test_duplicate_ids_are_rejected() -> None:
    mission = generate_mission(small_config())
    with pytest.raises(ValueError, match="duplicate observation IDs"):
        build_features(
            [mission.observations[0], mission.observations[0]], mission.anchors
        )
    with pytest.raises(ValueError, match="duplicate sample IDs"):
        build_features(mission.observations, [mission.anchors[0], mission.anchors[0]])


def test_mismatched_labels_rejected_before_writing(tmp_path: Path) -> None:
    from simulator.mission_generator import SyntheticMission

    mission = generate_mission(small_config())
    changed = SyntheticMission.model_validate({**mission.model_dump(), "labels": {}})
    with pytest.raises(ValueError, match="labels and sample IDs"):
        export_dataset(changed, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
