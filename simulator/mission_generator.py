"""Small configurable scenario generator. Relationships are synthetic assumptions."""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

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

Scenario = Literal["baseline", "elevated_co2", "sleep_deprivation", "recent_exercise"]
SCENARIOS: tuple[Scenario, ...] = (
    "baseline",
    "elevated_co2",
    "sleep_deprivation",
    "recent_exercise",
)
PIPELINE_METRICS = (
    "heart_rate",
    "cabin_co2_partial_pressure",
    "sleep_duration",
    "fatigue_self_report",
    "communication_delay",
    "exercise_active",
)


class SimulationConfig(Contract):
    seed: Annotated[int, Field(strict=True, ge=0)] = 42
    episodes_per_scenario: Annotated[int, Field(strict=True, gt=0, le=1000)] = 8
    steps: Annotated[int, Field(strict=True, gt=0, le=10000)] = 30
    step_seconds: Annotated[int, Field(strict=True, gt=0)] = 60
    start: AwareDatetime = datetime(2026, 11, 13, tzinfo=UTC)
    missing_probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.03
    noise_scale: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1.0
    baseline_heart_rate: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 72.0
    baseline_co2_pa: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 50.0
    co2_increase_pa: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 120.0
    co2_heart_rate_increase: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 18.0
    baseline_sleep_hours: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 8.0
    deprived_sleep_hours: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 3.0
    exercise_heart_rate_increase: Annotated[float, Field(ge=0, allow_inf_nan=False)] = (
        45.0
    )
    exercise_decay_minutes: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 15.0
    communication_delay_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] = (
        2.0
    )
    max_ingestion_delay_seconds: Annotated[int, Field(strict=True, ge=0)] = 120

    @field_validator("start")
    @classmethod
    def utc_start(cls, value: datetime) -> datetime:
        if value.fold:
            raise ValueError("resolve ambiguous start time before simulation")
        return value.astimezone(UTC)


class SyntheticMission(Contract):
    config: SimulationConfig
    observations: tuple[Observation, ...]
    anchors: tuple[SampleAnchor, ...]
    labels: dict[str, Scenario]


def _measurement(
    metric: str,
    scenario: Scenario,
    elapsed_minutes: float,
    rng: random.Random,
    config: SimulationConfig,
    personal_offset: float,
) -> Measurement:
    """Toy effects, not established exposure-response laws or medical ranges."""
    if metric == "exercise_active":
        return BooleanMeasurement(
            kind="boolean",
            value=(
                scenario == "recent_exercise"
                and elapsed_minutes < config.exercise_decay_minutes
            ),
        )
    if metric == "fatigue_self_report":
        states = ("rested", "tired", "very_tired")
        weights = (1, 3, 6) if scenario == "sleep_deprivation" else (7, 2, 1)
        return CategoricalMeasurement(
            kind="categorical", value=rng.choices(states, weights=weights)[0]
        )
    value: float
    if metric == "heart_rate":
        value = config.baseline_heart_rate + personal_offset
        if scenario == "elevated_co2":
            value += config.co2_heart_rate_increase
        if scenario == "recent_exercise":
            value += config.exercise_heart_rate_increase / (
                1 + elapsed_minutes / config.exercise_decay_minutes
            )
        value += rng.uniform(-3, 3) * config.noise_scale
    elif metric == "cabin_co2_partial_pressure":
        value = config.baseline_co2_pa + (
            config.co2_increase_pa if scenario == "elevated_co2" else 0
        )
        value += rng.uniform(-5, 5) * config.noise_scale
    elif metric == "sleep_duration":
        value = (
            config.deprived_sleep_hours
            if scenario == "sleep_deprivation"
            else config.baseline_sleep_hours
        )
        value += rng.uniform(-0.5, 0.5) * config.noise_scale
    elif metric == "communication_delay":
        value = (
            config.communication_delay_seconds
            + rng.uniform(-0.2, 0.2) * config.noise_scale
        )
    else:
        raise ValueError("unsupported simulator metric")
    unit = METRIC_REGISTRY[metric].canonical_unit
    assert unit is not None
    return NumericMeasurement(
        kind="numeric", value=round(max(0.0, value), 6), unit=unit
    )


def generate_mission(config: SimulationConfig) -> SyntheticMission:
    rng = random.Random(config.seed)
    scenarios = list(SCENARIOS) * config.episodes_per_scenario
    rng.shuffle(scenarios)
    observations: list[Observation] = []
    anchors: list[SampleAnchor] = []
    labels: dict[str, Scenario] = {}
    for scenario in scenarios:
        episode = f"episode-{rng.getrandbits(128):032x}"
        mission_id = f"mission-{episode}"
        offset = rng.uniform(-8, 8) * config.noise_scale
        astronaut = AstronautScope(
            kind="astronaut", astronaut_id="synthetic-crew", mission_id=mission_id
        )
        cabin = CompartmentScope(
            kind="compartment",
            spacecraft_id="synthetic-ship",
            compartment_id="synthetic-cabin",
            mission_id=mission_id,
        )
        ship = SpacecraftScope(
            kind="spacecraft", spacecraft_id="synthetic-ship", mission_id=mission_id
        )
        for step in range(config.steps):
            timestamp = config.start + timedelta(seconds=step * config.step_seconds)
            sample_id = hashlib.sha256(
                f"{episode}:{timestamp.isoformat()}".encode()
            ).hexdigest()[:32]
            anchors.append(
                SampleAnchor(
                    sample_id=sample_id,
                    episode_id=episode,
                    mission_id=mission_id,
                    astronaut_id=astronaut.astronaut_id,
                    spacecraft_id=cabin.spacecraft_id,
                    compartment_id=cabin.compartment_id,
                    timestamp=timestamp,
                )
            )
            labels[sample_id] = scenario
            for metric in PIPELINE_METRICS:
                scope: Scope = (
                    cabin
                    if metric == "cabin_co2_partial_pressure"
                    else ship
                    if metric == "communication_delay"
                    else astronaut
                )
                measurement = _measurement(
                    metric,
                    scenario,
                    step * config.step_seconds / 60,
                    rng,
                    config,
                    offset,
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
                            source_id="careyonda-synthetic-v1",
                            method="toy_scenario",
                            origin="simulated",
                            simulation=SimulationMetadata(
                                scenario_id=scenario,
                                run_id=episode,
                                generator_version="1.0.0",
                                seed=config.seed,
                            ),
                        ),
                    )
                )
    observations.sort(key=lambda item: (item.timestamp, item.observation_id))
    anchors.sort(key=lambda item: (item.timestamp, item.sample_id))
    return SyntheticMission(
        config=config,
        observations=tuple(observations),
        anchors=tuple(anchors),
        labels=labels,
    )
