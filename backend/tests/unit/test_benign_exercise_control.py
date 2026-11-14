"""Focused tests for the isolated Model B benign exercise-control extension."""

from __future__ import annotations

from collections import Counter

from app.features.temporal_features import build_features, feature_schema
from simulator.mission_generator import SimulationConfig, generate_mission
from simulator.research.benign_exercise_control import (
    BENIGN_EXERCISE_CONTROL,
    BenignExerciseControlConfig,
    generate_model_b_research_mission,
)


def small_config(seed: int = 42) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        episodes_per_scenario=1,
        steps=3,
        missing_probability=0,
        noise_scale=0,
    )


def test_control_is_additive_and_existing_scenarios_are_unchanged() -> None:
    config = small_config()
    core = generate_mission(config)
    research = generate_model_b_research_mission(
        config, BenignExerciseControlConfig(episode_count=3)
    )

    existing_observations = tuple(
        observation
        for observation in research.observations
        if observation.provenance.simulation is not None
        and observation.provenance.simulation.scenario_id != BENIGN_EXERCISE_CONTROL
    )
    assert existing_observations == core.observations
    core_episode_ids = {anchor.episode_id for anchor in core.anchors}
    research_episode_ids = {anchor.episode_id for anchor in research.anchors}
    control_episode_ids = research_episode_ids - core_episode_ids
    assert len(control_episode_ids) == 3
    assert core_episode_ids.isdisjoint(control_episode_ids)
    assert len(research.anchors) == len(core.anchors) + 3 * config.steps


def test_control_labels_and_predictors_are_separate() -> None:
    mission = generate_model_b_research_mission(
        small_config(), BenignExerciseControlConfig(episode_count=1)
    )
    labels_by_scenario: dict[str, set[bool]] = {}
    for label in mission.labels.values():
        labels_by_scenario.setdefault(label.scenario, set()).add(
            label.expected_anomaly_proxy
        )

    assert labels_by_scenario == {
        "baseline": {False},
        "elevated_co2": {True},
        "recent_exercise": {True},
        "sleep_deprivation": {True},
        BENIGN_EXERCISE_CONTROL: {False},
    }
    scenario_by_episode = {
        anchor.episode_id: mission.labels[anchor.sample_id].scenario
        for anchor in mission.anchors
    }
    assert all(
        observation.provenance.simulation is not None
        and observation.provenance.simulation.scenario_id
        == scenario_by_episode[observation.provenance.simulation.run_id]
        for observation in mission.observations
    )
    control_sample_ids = {
        sample_id
        for sample_id, label in mission.labels.items()
        if label.scenario == BENIGN_EXERCISE_CONTROL
    }
    control_episodes = {
        anchor.episode_id
        for anchor in mission.anchors
        if anchor.sample_id in control_sample_ids
    }
    control_observations = tuple(
        observation
        for observation in mission.observations
        if observation.provenance.simulation is not None
        and observation.provenance.simulation.scenario_id == BENIGN_EXERCISE_CONTROL
    )
    assert len(control_episodes) == 1
    assert len(control_sample_ids) == small_config().steps
    assert {observation.metric for observation in control_observations} == {
        "heart_rate",
        "cabin_co2_partial_pressure",
        "sleep_duration",
        "fatigue_self_report",
        "communication_delay",
        "exercise_active",
    }
    assert all(
        mission.labels[anchor.sample_id].scenario == BENIGN_EXERCISE_CONTROL
        and mission.labels[anchor.sample_id].expected_anomaly_proxy is False
        for anchor in mission.anchors
        if anchor.episode_id in control_episodes
    )

    samples = build_features(mission.observations, mission.anchors)
    schema_features = feature_schema(300)["features"]
    assert isinstance(schema_features, list)
    expected_names: list[str] = []
    nullable_by_name: dict[str, bool] = {}
    for feature in schema_features:
        assert isinstance(feature, dict)
        name = feature.get("name")
        nullable = feature.get("nullable")
        assert isinstance(name, str)
        assert type(nullable) is bool
        expected_names.append(name)
        nullable_by_name[name] = nullable
    assert not any("scenario" in name or "label" in name for name in expected_names)
    for sample in samples:
        assert tuple(sample.values) == tuple(expected_names)
        assert all(
            nullable_by_name[name] if value is None else type(value) is float
            for name, value in sample.values.items()
        )


def test_benign_control_has_separate_exercise_response_signature() -> None:
    mission = generate_model_b_research_mission(
        small_config(),
        BenignExerciseControlConfig(episode_count=1, response_fraction=0.5),
    )
    samples = build_features(mission.observations, mission.anchors)
    by_scenario: dict[str, list[dict[str, float | None]]] = {}
    for sample in samples:
        label = mission.labels[sample.anchor.sample_id]
        by_scenario.setdefault(label.scenario, []).append(sample.values)

    benign = by_scenario[BENIGN_EXERCISE_CONTROL][0]
    recent = by_scenario["recent_exercise"][0]
    assert benign["exercise_active_latest"] == recent["exercise_active_latest"] == 1.0
    assert benign["heart_rate_latest"] == 94.5
    assert recent["heart_rate_latest"] == 117.0
    assert (
        mission.labels[
            next(
                anchor.sample_id
                for anchor in mission.anchors
                if mission.labels[anchor.sample_id].scenario == BENIGN_EXERCISE_CONTROL
            )
        ].expected_anomaly_proxy
        is False
    )


def test_seed_reproducibility_and_distinct_episode_ids() -> None:
    first = generate_model_b_research_mission(
        small_config(42), BenignExerciseControlConfig(episode_count=1)
    )
    repeated = generate_model_b_research_mission(
        small_config(42), BenignExerciseControlConfig(episode_count=1)
    )
    different_seed = generate_model_b_research_mission(
        small_config(43), BenignExerciseControlConfig(episode_count=1)
    )

    assert first.observations == repeated.observations
    assert first.anchors == repeated.anchors
    assert dict(first.labels) == dict(repeated.labels)
    first_episode_ids = {anchor.episode_id for anchor in first.anchors}
    other_episode_ids = {anchor.episode_id for anchor in different_seed.anchors}
    assert first_episode_ids.isdisjoint(other_episode_ids)
    assert Counter(label.scenario for label in first.labels.values()) == Counter(
        {
            "baseline": 3,
            "elevated_co2": 3,
            "recent_exercise": 3,
            "sleep_deprivation": 3,
            BENIGN_EXERCISE_CONTROL: 3,
        }
    )


def test_missing_control_measurements_remain_missing_in_features() -> None:
    config = small_config().model_copy(update={"missing_probability": 1.0})
    mission = generate_model_b_research_mission(
        config, BenignExerciseControlConfig(episode_count=1)
    )

    control_samples = tuple(
        sample
        for sample in build_features(mission.observations, mission.anchors)
        if mission.labels[sample.anchor.sample_id].scenario == BENIGN_EXERCISE_CONTROL
    )
    assert control_samples
    for sample in control_samples:
        assert all(
            sample.values[name] is None
            for name in sample.values
            if name.endswith("_latest") or name.endswith("_mean")
        )
        assert all(
            sample.values[name] == 1.0
            for name in sample.values
            if name.endswith("_missing")
        )
