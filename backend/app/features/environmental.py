"""Separate causal ISS environmental features; no training or synthetic pairing."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from statistics import fmean

from app.quality.validator import evaluate_quality
from app.schemas.observation import (
    METRIC_REGISTRY,
    NumericMeasurement,
    Observation,
    SpacecraftScope,
)

ENVIRONMENT_METRICS = (
    "cabin_co2_concentration",
    "environment_temperature",
    "relative_humidity",
)


@dataclass(frozen=True)
class EnvironmentSample:
    sample_id: str
    timestamp: datetime
    values: dict[str, float | None]
    evidence: dict[str, tuple[str, ...]]
    current_observation_ids: tuple[str, ...]


def environmental_schema() -> dict[str, object]:
    features: list[dict[str, object]] = []
    for metric in ENVIRONMENT_METRICS:
        for suffix in ("value", "mean_30m", "delta", "count_30m", "missing"):
            features.append(
                {
                    "name": f"{metric}_{suffix}",
                    "metric": metric,
                    "unit": "1"
                    if suffix in {"count_30m", "missing"}
                    else METRIC_REGISTRY[metric].canonical_unit,
                    "nullable": suffix not in {"count_30m", "missing"},
                }
            )
    features.append({"name": "gap_seconds", "unit": "s", "nullable": True})
    return {
        "schema_version": "1.0.0",
        "features": features,
        "metadata_columns": ["sample_id", "event_time_utc"],
        "window_seconds": 1800,
        "window": "(t-1800 seconds,t]",
        "mean": "arithmetic sample mean; not time-weighted",
        "delta": "current valid value minus most recent earlier valid value within window",
        "missing": "current timestamp has no unique evaluated-valid value; not zero imputation",
        "split_policy": "chronological 70/15/15 by unique timestamps; windows reset per split",
        "scope": "NASA-RR1 ISS only; no ground, radiation, or human physiological pairing",
        "scaling": "none; fit preprocessing only on training split",
    }


def iss_environment(observations: Sequence[Observation]) -> tuple[Observation, ...]:
    selected = [
        o
        for o in observations
        if o.metric in ENVIRONMENT_METRICS
        and isinstance(o.scope, SpacecraftScope)
        and o.scope.spacecraft_id == "ISS"
        and o.scope.mission_id == "NASA-RR1"
    ]
    if len({o.observation_id for o in selected}) != len(selected):
        raise ValueError("duplicate observation IDs")
    return tuple(sorted(selected, key=lambda o: (o.timestamp, o.observation_id)))


def build_environment_features(
    observations: Sequence[Observation],
) -> tuple[EnvironmentSample, ...]:
    """30-minute causal sample windows with actual irregular event timestamps."""
    grouped: dict[datetime, list[Observation]] = defaultdict(list)
    for observation in iss_environment(observations):
        grouped[observation.timestamp].append(observation)
    history: dict[str, deque[Observation]] = {
        metric: deque() for metric in ENVIRONMENT_METRICS
    }
    previous_time: datetime | None = None
    previous_ids: tuple[str, ...] = ()
    samples: list[EnvironmentSample] = []
    for timestamp, current in sorted(grouped.items()):
        values: dict[str, float | None] = {}
        evidence: dict[str, tuple[str, ...]] = {}
        for metric in ENVIRONMENT_METRICS:
            window = history[metric]
            while window and window[0].timestamp <= timestamp - timedelta(seconds=1800):
                window.popleft()
            previous = window[-1] if window else None
            candidates = [
                o
                for o in current
                if o.metric == metric and evaluate_quality(o).status == "valid"
            ]
            chosen = candidates[0] if len(candidates) == 1 else None
            current_value: float | None = None
            if chosen is not None:
                assert isinstance(chosen.measurement, NumericMeasurement)
                current_value = chosen.measurement.value
                window.append(chosen)
            numeric_values = []
            for item in window:
                assert isinstance(item.measurement, NumericMeasurement)
                numeric_values.append(item.measurement.value)
            current_ids = (chosen.observation_id,) if chosen is not None else ()
            current_metric_ids = tuple(
                o.observation_id for o in current if o.metric == metric
            )
            prior_value = None
            if previous is not None:
                assert isinstance(previous.measurement, NumericMeasurement)
                prior_value = previous.measurement.value
            values.update(
                {
                    f"{metric}_value": current_value,
                    f"{metric}_mean_30m": fmean(numeric_values)
                    if numeric_values
                    else None,
                    f"{metric}_delta": current_value - prior_value
                    if current_value is not None and prior_value is not None
                    else None,
                    f"{metric}_count_30m": float(len(numeric_values)),
                    f"{metric}_missing": float(chosen is None),
                }
            )
            evidence.update(
                {
                    f"{metric}_value": current_ids,
                    f"{metric}_mean_30m": tuple(o.observation_id for o in window),
                    f"{metric}_delta": (
                        *(
                            (previous.observation_id,)
                            if previous is not None and chosen is not None
                            else ()
                        ),
                        *current_ids,
                    ),
                    f"{metric}_count_30m": tuple(o.observation_id for o in window),
                    f"{metric}_missing": current_metric_ids,
                }
            )
        values["gap_seconds"] = (
            (timestamp - previous_time).total_seconds()
            if previous_time is not None
            else None
        )
        evidence["gap_seconds"] = (
            (*previous_ids, *(o.observation_id for o in current))
            if previous_time is not None
            else ()
        )
        oid_tuple = tuple(o.observation_id for o in current)
        sid = sha256(
            f"rr1-environment-v1:{timestamp.isoformat()}:{oid_tuple}".encode()
        ).hexdigest()[:32]
        samples.append(EnvironmentSample(sid, timestamp, values, evidence, oid_tuple))
        previous_time = timestamp
        previous_ids = oid_tuple
    return tuple(samples)


def chronological_features(
    observations: Sequence[Observation],
) -> dict[str, tuple[EnvironmentSample, ...]]:
    selected = iss_environment(observations)
    times = sorted({o.timestamp for o in selected})
    train_end, validation_end = int(len(times) * 0.70), int(len(times) * 0.85)
    if not 0 < train_end < validation_end < len(times):
        raise ValueError(
            "at least enough unique timestamps for three nonempty splits are required"
        )
    assignments = {
        timestamp: "train"
        if i < train_end
        else "validation"
        if i < validation_end
        else "test"
        for i, timestamp in enumerate(times)
    }
    partitions: dict[str, list[Observation]] = {
        name: [] for name in ("train", "validation", "test")
    }
    for observation in selected:
        partitions[assignments[observation.timestamp]].append(observation)
    return {
        name: build_environment_features(records)
        for name, records in partitions.items()
    }
