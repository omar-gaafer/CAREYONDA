"""M4.2 research contracts; validation only, never reference estimation."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil, isclose, isfinite
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BeforeValidator,
    Field,
    StrictFloat,
    model_validator,
)

from app.schemas.observation import (
    METRIC_REGISTRY,
    Contract,
    Identifier,
    NumericMeasurement,
    Observation,
)


def _parse_time(value: object) -> object:
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        raise ValueError("timestamp requires aware datetime or ISO 8601 text")
    return value


def _utc(value: datetime) -> datetime:
    if value.fold:
        raise ValueError("folded local time requires explicit UTC resolution")
    return value.astimezone(UTC)


def unique_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    """Validate identity lists without discarding ordering or duplicates."""
    if len(set(values)) != len(values):
        raise ValueError("identifiers must be unique")
    return values


ResearchTime = Annotated[
    AwareDatetime, BeforeValidator(_parse_time), AfterValidator(_utc)
]
Finite = Annotated[StrictFloat, Field(allow_inf_nan=False)]
Nonnegative = Annotated[Finite, Field(ge=0)]
Positive = Annotated[Finite, Field(gt=0)]
Fraction = Annotated[Finite, Field(ge=0, le=1)]
Count = Annotated[int, Field(strict=True, ge=0)]
PositiveCount = Annotated[int, Field(strict=True, gt=0)]
Ids = Annotated[tuple[Identifier, ...], AfterValidator(unique_ids)]
Reasons = Annotated[Ids, Field(min_length=1)]
Text = Annotated[str, Field(strict=True, min_length=1, pattern=r"\S")]
Version = Annotated[str, Field(strict=True, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
AvailabilityMode = Literal["retrospective", "prospective"]


class ResearchContract(Contract):
    schema_version: Literal["1.0.0"]
    interpretation: Literal["research_only"]


class TimeInterval(Contract):
    """Event support interval [start, end]; point support has equal endpoints."""

    start: ResearchTime
    end: ResearchTime

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("interval start must not follow end")
        return self


class SourceScope(Contract):
    dataset_id: Identifier
    run_id: Identifier
    mission_id: Identifier
    subject_id: Identifier
    source_id: Identifier
    sensor_id: Identifier | None
    sensor_epoch: Identifier | None
    data_origin: Literal["synthetic", "real", "unknown"]

    @model_validator(mode="after")
    def sensor_pair(self) -> Self:
        if (self.sensor_id is None) != (self.sensor_epoch is None):
            raise ValueError("sensor identity and epoch must be supplied together")
        return self


class ResearchEvidence(Contract):
    """Original observation plus explicit research context, never a new reading."""

    observation: Observation
    dataset_id: Identifier
    run_id: Identifier
    sensor_id: Identifier | None
    sensor_epoch: Identifier | None
    data_origin: Literal["synthetic", "real", "unknown"]
    temporal_support: TimeInterval

    @model_validator(mode="after")
    def consistent_metadata(self) -> Self:
        if (self.sensor_id is None) != (self.sensor_epoch is None):
            raise ValueError("sensor identity and epoch must be supplied together")
        obs = self.observation
        if (
            not self.temporal_support.start
            <= obs.timestamp
            <= self.temporal_support.end
        ):
            raise ValueError("observation timestamp must lie within temporal support")
        if obs.provenance.origin == "simulated":
            if self.data_origin != "synthetic":
                raise ValueError("simulated provenance requires synthetic origin")
            simulation = obs.provenance.simulation
            if simulation is None or simulation.run_id != self.run_id:
                raise ValueError("simulation run must match research run")
        if obs.provenance.origin in {"measured", "self_reported"}:
            if self.data_origin != "real":
                raise ValueError("measured provenance requires real origin")
        return self

    def available_at(self, decision_time: datetime, mode: AvailabilityMode) -> bool:
        """Check declared availability only; does not retrieve/select evidence."""
        ingested = self.observation.ingested_at
        return mode == "retrospective" or (
            ingested is not None
            and ingested <= decision_time
            and self.temporal_support.end <= decision_time
        )

    def matches(self, scope: SourceScope, metric: str, unit: str) -> bool:
        obs = self.observation
        return (
            self.dataset_id == scope.dataset_id
            and self.run_id == scope.run_id
            and obs.scope.mission_id == scope.mission_id
            and obs.scope.kind == "astronaut"
            and obs.scope.astronaut_id == scope.subject_id
            and obs.provenance.source_id == scope.source_id
            and self.sensor_id == scope.sensor_id
            and self.sensor_epoch == scope.sensor_epoch
            and self.data_origin == scope.data_origin
            and obs.metric == metric
            and isinstance(obs.measurement, NumericMeasurement)
            and obs.measurement.unit == unit
        )


class ExcludedEvidence(Contract):
    evidence: ResearchEvidence
    reason_codes: Reasons


def validate_numeric_metric(metric: str, unit: str, *, personal: bool = False) -> None:
    definition = METRIC_REGISTRY.get(metric)
    if (
        definition is None
        or definition.measurement_kind != "numeric"
        or definition.canonical_unit != unit
        or (personal and "astronaut" not in definition.scopes)
    ):
        raise ValueError("unsupported metric, scope or canonical unit; no conversion")


class BaselinePolicy(ResearchContract):
    policy_id: Identifier
    policy_version: Version
    source_scope: SourceScope
    metric: Identifier
    unit: Text
    reference_interval: TimeInterval
    bin_duration_seconds: Positive
    minimum_occupied_bins: PositiveCount
    minimum_observed_span_seconds: Positive
    minimum_occupancy_fraction: Annotated[Fraction, Field(gt=0)]
    maximum_gap_seconds: Positive
    maximum_reference_age_seconds: Positive
    source_sensor_compatibility: Literal["exact_identity", "unavailable"]
    availability_mode: AvailabilityMode

    @model_validator(mode="after")
    def valid_policy(self) -> Self:
        validate_numeric_metric(self.metric, self.unit, personal=True)
        duration = (
            self.reference_interval.end - self.reference_interval.start
        ).total_seconds()
        if duration <= 0 or self.bin_duration_seconds > duration:
            raise ValueError("reference interval must contain at least one bin")
        capacity = duration / self.bin_duration_seconds
        if not isfinite(capacity):
            raise ValueError("reference bin capacity must be representable")
        if self.minimum_occupied_bins > ceil(capacity):
            raise ValueError("minimum occupied bins exceeds reference capacity")
        if self.minimum_observed_span_seconds > duration:
            raise ValueError("minimum span exceeds reference interval")
        if self.source_sensor_compatibility == "exact_identity" and (
            self.source_scope.sensor_id is None
            or self.source_scope.data_origin == "unknown"
        ):
            raise ValueError("exact compatibility requires known sensor and origin")
        return self


class ReferenceBin(Contract):
    """Index into (start+i*duration, min(end,start+(i+1)*duration)]."""

    index: Count
    observation_ids: Annotated[Ids, Field(min_length=1)]


class ReferenceSummary(Contract):
    total_bins: PositiveCount
    occupied_bins: Count
    sample_count: Count
    occupancy_fraction: Fraction
    observed_span_seconds: Nonnegative
    maximum_gap_seconds: Nonnegative
    bins: tuple[ReferenceBin, ...]

    @model_validator(mode="after")
    def consistent_counts(self) -> Self:
        indices = [b.index for b in self.bins]
        ids = tuple(i for b in self.bins for i in b.observation_ids)
        unique_ids(ids)
        if len(set(indices)) != len(indices) or any(
            i >= self.total_bins for i in indices
        ):
            raise ValueError("bin indices must be unique and within capacity")
        if self.occupied_bins != len(self.bins) or self.sample_count != len(ids):
            raise ValueError("bin and sample counts must match evidence lists")
        if not isclose(
            self.occupancy_fraction, self.occupied_bins / self.total_bins, abs_tol=1e-12
        ):
            raise ValueError("occupancy fraction must equal occupied / total bins")
        if self.sample_count < 2 and (
            self.observed_span_seconds != 0 or self.maximum_gap_seconds != 0
        ):
            raise ValueError("fewer than two readings cannot have temporal spread")
        return self


class BaselineProfile(ResearchContract):
    profile_id: Identifier
    policy: BaselinePolicy
    assessed_at: ResearchTime
    included: tuple[ResearchEvidence, ...]
    excluded: tuple[ExcludedEvidence, ...]
    summary: ReferenceSummary
    median_value: Finite | None
    raw_mad: Nonnegative | None
    status: Literal["ready", "unsupported", "insufficient_reference", "flat_reference"]
    abstention_reasons: Ids
    method_version: Identifier

    @model_validator(mode="after")
    def valid_profile(self) -> Self:
        policy = self.policy
        interval = policy.reference_interval
        if self.assessed_at < interval.end:
            raise ValueError("assessment cannot precede reference end")
        ids = tuple(e.observation.observation_id for e in self.included)
        unique_ids(
            ids + tuple(e.evidence.observation.observation_id for e in self.excluded)
        )
        bin_ids = tuple(i for b in self.summary.bins for i in b.observation_ids)
        if set(ids) != set(bin_ids):
            raise ValueError("included evidence must match bin lineage")
        duration = (interval.end - interval.start).total_seconds()
        if self.summary.total_bins != ceil(duration / policy.bin_duration_seconds):
            raise ValueError("bin capacity must match policy interval")
        lookup = {e.observation.observation_id: e for e in self.included}
        for b in self.summary.bins:
            for oid in b.observation_ids:
                obs = lookup[oid].observation
                offset = (obs.timestamp - interval.start).total_seconds()
                if (
                    not b.index * policy.bin_duration_seconds
                    < offset
                    <= min(duration, (b.index + 1) * policy.bin_duration_seconds)
                ):
                    raise ValueError("evidence event time falls outside declared bin")
        for e in self.included:
            if not e.matches(policy.source_scope, policy.metric, policy.unit):
                raise ValueError(
                    "included evidence differs from policy scope or sensor"
                )
            if e.observation.quality.status != "valid":
                raise ValueError("baseline may include evaluated-valid evidence only")
            if not e.available_at(self.assessed_at, policy.availability_mode):
                raise ValueError("prospective evidence unavailable at assessment time")
            if (
                e.temporal_support.start <= interval.start
                or e.temporal_support.end > interval.end
            ):
                raise ValueError("included temporal support must fit reference window")
        simultaneous: dict[datetime, str] = {}
        for e in self.included:
            obs = e.observation
            measurement = obs.measurement.model_dump_json()
            if (
                obs.timestamp in simultaneous
                and simultaneous[obs.timestamp] != measurement
            ):
                raise ValueError("conflicting simultaneous readings cannot be included")
            simultaneous[obs.timestamp] = measurement
        times = sorted(e.observation.timestamp for e in self.included)
        span = (times[-1] - times[0]).total_seconds() if times else 0.0
        gaps = [
            (later - earlier).total_seconds()
            for earlier, later in zip(times, times[1:], strict=False)
        ]
        if not isclose(self.summary.observed_span_seconds, span, abs_tol=1e-12):
            raise ValueError("declared observed span must match evidence timestamps")
        if not isclose(
            self.summary.maximum_gap_seconds, max(gaps, default=0.0), abs_tol=1e-12
        ):
            raise ValueError("declared maximum gap must match evidence timestamps")
        if self.summary.observed_span_seconds > duration:
            raise ValueError("observed span exceeds reference interval")
        if self.summary.maximum_gap_seconds > self.summary.observed_span_seconds:
            raise ValueError("maximum gap exceeds observed span")
        if (self.median_value is None) != (self.raw_mad is None):
            raise ValueError("median and MAD must be present or absent together")
        if (self.status == "ready") == bool(self.abstention_reasons):
            raise ValueError("only ready profiles may omit abstention reasons")
        if self.status in {"ready", "flat_reference"}:
            if policy.source_sensor_compatibility != "exact_identity":
                raise ValueError("usable reference requires configured compatibility")
            if self.median_value is None or self.raw_mad is None:
                raise ValueError("usable reference requires median and raw MAD")
            if (self.raw_mad == 0) != (self.status == "flat_reference"):
                raise ValueError("zero MAD requires flat_reference; never use epsilon")
            s = self.summary
            if (
                s.occupied_bins < policy.minimum_occupied_bins
                or s.observed_span_seconds < policy.minimum_observed_span_seconds
                or s.occupancy_fraction < policy.minimum_occupancy_fraction
                or s.maximum_gap_seconds > policy.maximum_gap_seconds
                or (self.assessed_at - interval.end).total_seconds()
                > policy.maximum_reference_age_seconds
            ):
                raise ValueError(
                    "usable reference fails declared coverage or freshness"
                )
        elif self.median_value is not None:
            raise ValueError("unusable reference cannot publish reference statistics")
        if (
            policy.source_sensor_compatibility == "unavailable"
            and self.status != "unsupported"
        ):
            raise ValueError("unknown compatibility requires unsupported profile")
        return self
