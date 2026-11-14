"""Isolated Model B synthetic control for benign exercise-context research.

This extension leaves the core four-scenario generator unchanged. Its lower
exercise-related heart-rate response is a configurable toy contrast, not a
physiological normal range, clinical threshold, or validated exercise model.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import Field

from app.features.temporal_features import SampleAnchor
from app.schemas.observation import (
    METRIC_REGISTRY,
    AstronautScope,
    BooleanMeasurement,
    CategoricalMeasurement,
    CompartmentScope,
    Contract,
    DataQuality,
    Measurement,
    NumericMeasurement,
    Observation,
    Provenance,
    Scope,
    SimulationMetadata,
    SpacecraftScope,
    UnavailableMeasurement,
)
from simulator.mission_generator import (
    PIPELINE_METRICS,
    SimulationConfig,
    generate_mission,
)

BENIGN_EXERCISE_CONTROL: Literal["benign_exercise_control"] = "benign_exercise_control"
ResearchScenario = Literal[
    "baseline",
    "elevated_co2",
    "sleep_deprivation",
    "recent_exercise",
    "benign_exercise_control",
]


class BenignExerciseControlConfig(Contract):
    """Research-only control settings, separate from SimulationConfig."""

    episode_count: Annotated[int, Field(strict=True, ge=1, le=1000)] | None = None
    response_fraction: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] = 0.5


@dataclass(frozen=True)
class ResearchLabel:
    """Scenario metadata and synthetic evaluation proxy, never a predictor."""

    scenario: ResearchScenario
    expected_anomaly_proxy: bool


@dataclass(frozen=True)
class ModelBResearchMission:
    """In-memory combined mission with labels kept outside feature values."""

    config: SimulationConfig
    control_config: BenignExerciseControlConfig
    control_seed: int
    observations: tuple[Observation, ...]
    anchors: tuple[SampleAnchor, ...]
    labels: Mapping[str, ResearchLabel]


def _derive_control_seed(seed: int) -> int:
    """Create a deterministic RNG stream disjoint by scenario name/version."""
    material = f"careyonda:model-b:benign-exercise-control:v1:{seed}".encode()
    derived = int.from_bytes(hashlib.sha256(material).digest()[:16], "big")
    return derived + 1 if derived == seed else derived


def _numeric(metric: str, value: float) -> NumericMeasurement:
    unit = METRIC_REGISTRY[metric].canonical_unit
    if unit is None:
        raise ValueError("numeric metric is missing its canonical unit")
    return NumericMeasurement(
        kind="numeric", value=round(max(0.0, value), 6), unit=unit
    )


def _control_measurement(
    metric: str,
    elapsed_minutes: float,
    personal_offset: float,
    rng: random.Random,
    config: SimulationConfig,
    response_fraction: float,
) -> Measurement:
    """Generate the six established metrics under a lower-response exercise toy."""
    if metric == "exercise_active":
        return BooleanMeasurement(
            kind="boolean",
            value=elapsed_minutes < config.exercise_decay_minutes,
        )
    if metric == "fatigue_self_report":
        return CategoricalMeasurement(
            kind="categorical",
            value=rng.choices(("rested", "tired", "very_tired"), weights=(7, 2, 1))[0],
        )

    if metric == "heart_rate":
        value = (
            config.baseline_heart_rate
            + personal_offset
            + response_fraction
            * config.exercise_heart_rate_increase
            / (1 + elapsed_minutes / config.exercise_decay_minutes)
            + rng.uniform(-3, 3) * config.noise_scale
        )
    elif metric == "cabin_co2_partial_pressure":
        value = config.baseline_co2_pa + rng.uniform(-5, 5) * config.noise_scale
    elif metric == "sleep_duration":
        value = (
            config.baseline_sleep_hours + rng.uniform(-0.5, 0.5) * config.noise_scale
        )
    elif metric == "communication_delay":
        value = config.communication_delay_seconds + rng.uniform(-0.2, 0.2) * (
            config.noise_scale
        )
    else:
        raise ValueError("unsupported Model B research metric")
    return _numeric(metric, value)


def _generate_control_episodes(
    config: SimulationConfig,
    *,
    episode_count: int,
    control_seed: int,
    response_fraction: float,
    existing_episode_ids: set[str],
) -> tuple[list[Observation], list[SampleAnchor]]:
    rng = random.Random(control_seed)
    observations: list[Observation] = []
    anchors: list[SampleAnchor] = []
    used_episode_ids = set(existing_episode_ids)

    for _ in range(episode_count):
        episode_id = f"episode-{rng.getrandbits(128):032x}"
        while episode_id in used_episode_ids:
            episode_id = f"episode-{rng.getrandbits(128):032x}"
        used_episode_ids.add(episode_id)
        mission_id = f"mission-{episode_id}"
        personal_offset = rng.uniform(-8, 8) * config.noise_scale
        astronaut = AstronautScope(
            kind="astronaut", astronaut_id="synthetic-crew", mission_id=mission_id
        )
        compartment = CompartmentScope(
            kind="compartment",
            spacecraft_id="synthetic-ship",
            compartment_id="synthetic-cabin",
            mission_id=mission_id,
        )
        spacecraft = SpacecraftScope(
            kind="spacecraft", spacecraft_id="synthetic-ship", mission_id=mission_id
        )

        for step in range(config.steps):
            timestamp = config.start + timedelta(seconds=step * config.step_seconds)
            sample_id = hashlib.sha256(
                f"{episode_id}:{timestamp.isoformat()}".encode()
            ).hexdigest()[:32]
            anchors.append(
                SampleAnchor(
                    sample_id=sample_id,
                    episode_id=episode_id,
                    mission_id=mission_id,
                    astronaut_id=astronaut.astronaut_id,
                    spacecraft_id=compartment.spacecraft_id,
                    compartment_id=compartment.compartment_id,
                    timestamp=timestamp,
                )
            )
            for metric in PIPELINE_METRICS:
                scope: Scope = (
                    compartment
                    if metric == "cabin_co2_partial_pressure"
                    else spacecraft
                    if metric == "communication_delay"
                    else astronaut
                )
                measurement = _control_measurement(
                    metric,
                    step * config.step_seconds / 60,
                    personal_offset,
                    rng,
                    config,
                    response_fraction,
                )
                quality = DataQuality(status="valid")
                if rng.random() < config.missing_probability:
                    measurement = UnavailableMeasurement(
                        kind="unavailable", reason="not_received"
                    )
                    quality = DataQuality(
                        status="missing", reason_codes=("synthetic_dropout",)
                    )
                observations.append(
                    Observation(
                        schema_version="1.0.0",
                        observation_id=f"{sample_id}-{metric}",
                        timestamp=timestamp,
                        ingested_at=timestamp
                        + timedelta(
                            seconds=rng.randint(0, config.max_ingestion_delay_seconds)
                        ),
                        domain=METRIC_REGISTRY[metric].domain,
                        metric=metric,
                        scope=scope,
                        measurement=measurement,
                        quality=quality,
                        provenance=Provenance(
                            source_type="simulator",
                            source_id="careyonda-model-b-research",
                            method="benign_exercise_control_toy",
                            origin="simulated",
                            simulation=SimulationMetadata(
                                scenario_id=BENIGN_EXERCISE_CONTROL,
                                run_id=episode_id,
                                generator_version="model-b-research-1.0.0",
                                seed=control_seed,
                            ),
                        ),
                    )
                )

    return observations, anchors


def generate_model_b_research_mission(
    config: SimulationConfig,
    control_config: BenignExerciseControlConfig | None = None,
) -> ModelBResearchMission:
    """Add research-only benign exercise episodes without changing core output.

    The existing four-scenario mission is generated by the unchanged core
    generator. Control episodes use a SHA-256 domain-separated RNG stream,
    the same six metric contracts, the same temporal feature builder, and an
    explicitly separate expected-anomaly proxy label.
    """
    selected_control_config = control_config or BenignExerciseControlConfig()
    episode_count = (
        selected_control_config.episode_count
        if selected_control_config.episode_count is not None
        else config.episodes_per_scenario
    )
    base = generate_mission(config)
    base_episode_ids = {anchor.episode_id for anchor in base.anchors}
    control_seed = _derive_control_seed(config.seed)
    control_observations, control_anchors = _generate_control_episodes(
        config,
        episode_count=episode_count,
        control_seed=control_seed,
        response_fraction=selected_control_config.response_fraction,
        existing_episode_ids=base_episode_ids,
    )

    labels: dict[str, ResearchLabel] = {
        sample_id: ResearchLabel(
            scenario=scenario,
            expected_anomaly_proxy=scenario != "baseline",
        )
        for sample_id, scenario in base.labels.items()
    }
    labels.update(
        {
            anchor.sample_id: ResearchLabel(
                scenario=BENIGN_EXERCISE_CONTROL,
                expected_anomaly_proxy=False,
            )
            for anchor in control_anchors
        }
    )

    observations = tuple(
        sorted(
            (*base.observations, *control_observations),
            key=lambda item: (item.timestamp, item.observation_id),
        )
    )
    anchors = tuple(
        sorted(
            (*base.anchors, *control_anchors),
            key=lambda item: (item.timestamp, item.sample_id),
        )
    )
    if len({item.observation_id for item in observations}) != len(observations):
        raise ValueError("duplicate observation IDs across research scenarios")
    if len({item.sample_id for item in anchors}) != len(anchors):
        raise ValueError("duplicate sample IDs across research scenarios")
    if set(labels) != {anchor.sample_id for anchor in anchors}:
        raise ValueError("research labels and sample IDs must match exactly")

    return ModelBResearchMission(
        config=config,
        control_config=selected_control_config,
        control_seed=control_seed,
        observations=observations,
        anchors=anchors,
        labels=MappingProxyType(labels),
    )
