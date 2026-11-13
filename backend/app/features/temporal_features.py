"""Causal event-time features. No simulator or target-label dependencies."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean
from types import MappingProxyType

from pydantic import AwareDatetime, field_validator

from app.quality.validator import evaluate_quality
from app.schemas.observation import (
    METRIC_REGISTRY,
    AstronautScope,
    BooleanMeasurement,
    CategoricalMeasurement,
    CompartmentScope,
    Contract,
    Identifier,
    NumericMeasurement,
    Observation,
    SpacecraftScope,
)

FEATURE_METRICS = (
    "heart_rate",
    "cabin_co2_partial_pressure",
    "sleep_duration",
    "fatigue_self_report",
    "communication_delay",
    "exercise_active",
)
FATIGUE_ENCODING: Mapping[str, float] = MappingProxyType(
    {"rested": 0.0, "tired": 1.0, "very_tired": 2.0}
)


class SampleAnchor(Contract):
    """Label-free prediction context; identifiers are metadata, not predictors."""

    sample_id: Identifier
    episode_id: Identifier
    mission_id: Identifier
    astronaut_id: Identifier
    spacecraft_id: Identifier
    compartment_id: Identifier
    timestamp: AwareDatetime

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


@dataclass(frozen=True)
class FeatureSample:
    anchor: SampleAnchor
    values: dict[str, float | None]
    evidence: dict[str, tuple[str, ...]]
    window_observation_ids: tuple[str, ...]


def feature_schema(window_seconds: int) -> dict[str, object]:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    columns: list[dict[str, object]] = []
    for metric in FEATURE_METRICS:
        definition = METRIC_REGISTRY[metric]
        unit = definition.canonical_unit or "1"
        columns.extend(
            [
                {
                    "name": f"{metric}_latest",
                    "metric": metric,
                    "unit": unit,
                    "aggregation": "latest",
                    "nullable": True,
                },
                {
                    "name": f"{metric}_missing",
                    "metric": metric,
                    "unit": "1",
                    "aggregation": "no_usable_value",
                    "nullable": False,
                },
            ]
        )
        if definition.measurement_kind == "numeric":
            columns.append(
                {
                    "name": f"{metric}_mean",
                    "metric": metric,
                    "unit": unit,
                    "aggregation": "arithmetic_mean",
                    "nullable": True,
                }
            )
    return {
        "schema_version": "1.0.0",
        "observation_schema_version": "1.0.0",
        "identifier_columns": ["sample_id"],
        "features": columns,
        "window_seconds": window_seconds,
        "window": "(sample_time-window, sample_time]",
        "time_basis": "event_time",
        "availability": "retrospective_event_time_not_live_arrival",
        "quality_policy": "evaluated valid only; retain all records in evidence",
        "missing_values": "empty CSV cell; no imputation; missing flag means no usable value in window",
        "categorical_encoding": {"fatigue_self_report": dict(FATIGUE_ENCODING)},
        "boolean_encoding": {"false": 0, "true": 1},
        "scope_policy": "one astronaut; CO2 from specified compartment; communication delay from specified spacecraft",
    }


def _in_scope(observation: Observation, anchor: SampleAnchor) -> bool:
    scope = observation.scope
    if scope.mission_id != anchor.mission_id:
        return False
    if observation.metric == "cabin_co2_partial_pressure":
        return (
            isinstance(scope, CompartmentScope)
            and scope.spacecraft_id == anchor.spacecraft_id
            and scope.compartment_id == anchor.compartment_id
        )
    if observation.metric == "communication_delay":
        return (
            isinstance(scope, SpacecraftScope)
            and scope.spacecraft_id == anchor.spacecraft_id
        )
    return (
        isinstance(scope, AstronautScope) and scope.astronaut_id == anchor.astronaut_id
    )


def _number(observation: Observation) -> float:
    measurement = observation.measurement
    if isinstance(measurement, NumericMeasurement):
        return measurement.value
    if isinstance(measurement, BooleanMeasurement):
        return float(measurement.value)
    if isinstance(measurement, CategoricalMeasurement):
        return FATIGUE_ENCODING[measurement.value]
    raise ValueError("unavailable measurements cannot be encoded")


def build_features(
    observations: Sequence[Observation],
    anchors: Sequence[SampleAnchor],
    window_seconds: int = 300,
) -> tuple[FeatureSample, ...]:
    """Use only (t-window, t], with deterministic event-time/ID tie ordering.

    Ingestion time is intentionally not an ordering/filter key. This is an offline
    retrospective dataset, not a simulation of what had arrived at prediction time.
    """
    feature_schema(window_seconds)
    if len({o.observation_id for o in observations}) != len(observations):
        raise ValueError("duplicate observation IDs")
    if len({a.sample_id for a in anchors}) != len(anchors):
        raise ValueError("duplicate sample IDs")
    groups: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for observation in sorted(
        observations, key=lambda o: (o.timestamp, o.observation_id)
    ):
        groups[(observation.scope.mission_id, observation.metric)].append(observation)
    samples: list[FeatureSample] = []
    for anchor in sorted(anchors, key=lambda a: (a.timestamp, a.sample_id)):
        values: dict[str, float | None] = {}
        evidence: dict[str, tuple[str, ...]] = {}
        window_ids: list[str] = []
        lower = anchor.timestamp - timedelta(seconds=window_seconds)
        for metric in FEATURE_METRICS:
            window = [
                o
                for o in groups.get((anchor.mission_id, metric), [])
                if lower < o.timestamp <= anchor.timestamp and _in_scope(o, anchor)
            ]
            window_ids.extend(o.observation_id for o in window)
            usable = [o for o in window if evaluate_quality(o).status == "valid"]
            latest = f"{metric}_latest"
            missing = f"{metric}_missing"
            values[latest] = _number(usable[-1]) if usable else None
            values[missing] = float(not usable)
            evidence[latest] = (usable[-1].observation_id,) if usable else ()
            evidence[missing] = tuple(o.observation_id for o in window)
            if METRIC_REGISTRY[metric].measurement_kind == "numeric":
                mean = f"{metric}_mean"
                values[mean] = fmean(_number(o) for o in usable) if usable else None
                evidence[mean] = tuple(o.observation_id for o in usable)
        samples.append(
            FeatureSample(anchor, values, evidence, tuple(sorted(window_ids)))
        )
    return tuple(samples)
