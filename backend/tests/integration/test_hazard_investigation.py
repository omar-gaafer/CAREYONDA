"""Simulator -> exported observation JSON -> explainable investigation."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.ai.hazard_reasoning import investigate
from app.schemas.investigation import Investigation
from app.schemas.observation import Observation
from simulator.mission_generator import SCENARIOS, SimulationConfig, generate_mission
from simulator.run_simulation import export_dataset


def test_simulator_export_reasoning_without_training_changes(tmp_path: Path) -> None:
    reference = generate_mission(
        SimulationConfig(
            steps=3,
            episodes_per_scenario=1,
            noise_scale=0,
            missing_probability=0,
            start=datetime(2026, 11, 12, 23, tzinfo=UTC),
        )
    )
    reference_anchor = next(
        a
        for a in reversed(reference.anchors)
        if reference.labels[a.sample_id] == "baseline"
    )
    mission = generate_mission(
        SimulationConfig(
            steps=3, episodes_per_scenario=1, noise_scale=0, missing_probability=0
        )
    )
    export_dataset(mission, tmp_path / "dataset")
    observations = tuple(
        Observation.model_validate(o)
        for o in json.loads((tmp_path / "dataset" / "observations.json").read_text())
    )
    all_ids = {o.observation_id for o in (*observations, *reference.observations)}
    serialized_results = []
    for name in SCENARIOS:
        anchor = next(
            a for a in reversed(mission.anchors) if mission.labels[a.sample_id] == name
        )
        result = investigate(
            observations, anchor, reference.observations, reference_anchor
        )
        assert result.selected_hypothesis == name
        assert result.safety_status == "not_evaluated"
        for hypothesis in result.hypotheses:
            for finding in (
                *hypothesis.supporting_evidence,
                *hypothesis.contradictory_evidence,
                *hypothesis.missing_evidence,
            ):
                assert set(finding.observation_ids) <= all_ids
                assert set(finding.reference_observation_ids) <= all_ids
        serialized_results.append(result.model_dump(mode="json"))
        assert Investigation.model_validate_json(result.model_dump_json()) == result
    (tmp_path / "investigations.json").write_text(json.dumps(serialized_results))
    assert len(json.loads((tmp_path / "investigations.json").read_text())) == 4


@pytest.mark.parametrize("seed", [0, 42, 123])
def test_noisy_missing_simulator_runs_remain_deterministic_and_traceable(
    seed: int,
) -> None:
    reference = generate_mission(
        SimulationConfig(
            seed=seed,
            steps=5,
            episodes_per_scenario=1,
            start=datetime(2026, 11, 12, 23, tzinfo=UTC),
        )
    )
    reference_anchor = next(
        a
        for a in reversed(reference.anchors)
        if reference.labels[a.sample_id] == "baseline"
    )
    mission = generate_mission(
        SimulationConfig(
            seed=seed, steps=5, episodes_per_scenario=1, missing_probability=0.25
        )
    )
    for name in SCENARIOS:
        anchor = next(
            a for a in reversed(mission.anchors) if mission.labels[a.sample_id] == name
        )
        first = investigate(
            mission.observations, anchor, reference.observations, reference_anchor
        )
        second = investigate(
            tuple(reversed(mission.observations)),
            anchor,
            tuple(reversed(reference.observations)),
            reference_anchor,
        )
        assert first.model_dump_json() == second.model_dump_json()
        assert len(first.hypotheses) == 4
        assert first.uncertainty
        assert first.timestamp == anchor.timestamp
        assert not {
            "probability",
            "confidence",
            "diagnosis",
            "recommendation",
            "score",
        } & set(first.model_dump())
