"""Versioned, transport-independent observation contracts. No clinical thresholds."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    field_validator,
    model_validator,
)

Identifier = Annotated[
    str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
]
Domain = Literal[
    "physiological",
    "environmental",
    "radiation",
    "behavioral",
    "altered_gravity",
    "mission_context",
]
QualityStatus = Literal["valid", "suspect", "invalid", "missing", "unavailable"]


class Contract(BaseModel):
    """Reject unknown fields and prevent mutation after validation."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class AstronautScope(Contract):
    kind: Literal["astronaut"]
    astronaut_id: Identifier
    mission_id: Identifier


class SpacecraftScope(Contract):
    kind: Literal["spacecraft"]
    spacecraft_id: Identifier
    mission_id: Identifier


class CompartmentScope(Contract):
    kind: Literal["compartment"]
    spacecraft_id: Identifier
    compartment_id: Identifier
    mission_id: Identifier


class MissionScope(Contract):
    kind: Literal["mission"]
    mission_id: Identifier


Scope = Annotated[
    AstronautScope | SpacecraftScope | CompartmentScope | MissionScope,
    Field(discriminator="kind"),
]


class NumericMeasurement(Contract):
    kind: Literal["numeric"]
    value: Annotated[StrictFloat, Field(allow_inf_nan=False)]
    unit: Annotated[str, Field(strict=True, min_length=1, max_length=32)]


class BooleanMeasurement(Contract):
    kind: Literal["boolean"]
    value: StrictBool


class CategoricalMeasurement(Contract):
    kind: Literal["categorical"]
    value: Identifier


class UnavailableMeasurement(Contract):
    kind: Literal["unavailable"]
    reason: Literal["not_received", "not_collected", "sensor_offline", "rejected"]


Measurement = Annotated[
    NumericMeasurement
    | BooleanMeasurement
    | CategoricalMeasurement
    | UnavailableMeasurement,
    Field(discriminator="kind"),
]


class DataQuality(Contract):
    status: QualityStatus
    reason_codes: tuple[Identifier, ...] = ()
    sensor_confidence: (
        Annotated[StrictFloat, Field(ge=0, le=1, allow_inf_nan=False)] | None
    ) = None

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if self.status == "valid" and self.reason_codes:
            raise ValueError("valid status must not contain quality limitations")
        if self.status != "valid" and not self.reason_codes:
            raise ValueError("non-valid status requires reason codes")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("quality reason codes must be unique")
        if (
            self.status in {"missing", "unavailable"}
            and self.sensor_confidence is not None
        ):
            raise ValueError("absent measurements cannot carry sensor confidence")
        return self


class SimulationMetadata(Contract):
    scenario_id: Identifier
    run_id: Identifier
    generator_version: Identifier
    seed: Annotated[int, Field(strict=True, ge=0)]


class Provenance(Contract):
    source_type: Literal[
        "sensor", "crew_report", "computation", "simulator", "mission_log"
    ]
    source_id: Identifier
    method: Identifier
    origin: Literal["measured", "self_reported", "derived", "simulated"]
    parent_observation_ids: tuple[Identifier, ...] = ()
    transformation_version: Identifier | None = None
    simulation: SimulationMetadata | None = None

    @model_validator(mode="after")
    def validate_origin(self) -> Self:
        if len(set(self.parent_observation_ids)) != len(self.parent_observation_ids):
            raise ValueError("parent observation IDs must be unique")
        if self.origin == "derived":
            if not self.parent_observation_ids or self.transformation_version is None:
                raise ValueError(
                    "derived origin requires parents and transformation version"
                )
        elif self.parent_observation_ids or self.transformation_version is not None:
            raise ValueError("derivation metadata requires derived origin")
        if (self.origin == "simulated") != (self.simulation is not None):
            raise ValueError(
                "simulation metadata is required only for simulated origin"
            )
        allowed_sources = {
            "measured": {"sensor", "mission_log"},
            "self_reported": {"crew_report"},
            "derived": {"computation"},
            "simulated": {"simulator"},
        }
        if self.source_type not in allowed_sources[self.origin]:
            raise ValueError("source type is incompatible with origin")
        return self


class MetricDefinition(Contract):
    domain: Domain
    measurement_kind: Literal["numeric", "boolean", "categorical"]
    canonical_unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    categories: tuple[str, ...] = ()
    scopes: tuple[str, ...]


# Synthetic scenario starter vocabulary. Bounds are physical, never clinical.
METRIC_REGISTRY: Mapping[str, MetricDefinition] = MappingProxyType(
    {
        "cabin_co2_concentration": MetricDefinition(
            domain="environmental",
            measurement_kind="numeric",
            canonical_unit="ppm",
            minimum=0,
            scopes=("spacecraft", "mission"),
        ),
        "environment_temperature": MetricDefinition(
            domain="environmental",
            measurement_kind="numeric",
            canonical_unit="degC",
            minimum=-273.15,
            scopes=("spacecraft", "mission"),
        ),
        "relative_humidity": MetricDefinition(
            domain="environmental",
            measurement_kind="numeric",
            canonical_unit="%",
            minimum=0,
            maximum=100,
            scopes=("spacecraft", "mission"),
        ),
        "radiation_gcr_dose_rate": MetricDefinition(
            domain="radiation",
            measurement_kind="numeric",
            canonical_unit="mGy/d",
            minimum=0,
            scopes=("spacecraft",),
        ),
        "radiation_saa_dose_rate": MetricDefinition(
            domain="radiation",
            measurement_kind="numeric",
            canonical_unit="mGy/d",
            minimum=0,
            scopes=("spacecraft",),
        ),
        "radiation_total_dose_rate": MetricDefinition(
            domain="radiation",
            measurement_kind="numeric",
            canonical_unit="mGy/d",
            minimum=0,
            scopes=("spacecraft",),
        ),
        "radiation_accumulated_dose": MetricDefinition(
            domain="radiation",
            measurement_kind="numeric",
            canonical_unit="mGy",
            minimum=0,
            scopes=("spacecraft",),
        ),
        "cabin_co2_partial_pressure": MetricDefinition(
            domain="environmental",
            measurement_kind="numeric",
            canonical_unit="Pa",
            minimum=0,
            scopes=("spacecraft", "compartment"),
        ),
        "sleep_duration": MetricDefinition(
            domain="behavioral",
            measurement_kind="numeric",
            canonical_unit="h",
            minimum=0,
            scopes=("astronaut",),
        ),
        "fatigue_self_report": MetricDefinition(
            domain="behavioral",
            measurement_kind="categorical",
            categories=("rested", "tired", "very_tired"),
            scopes=("astronaut",),
        ),
        "communication_delay": MetricDefinition(
            domain="mission_context",
            measurement_kind="numeric",
            canonical_unit="s",
            minimum=0,
            scopes=("spacecraft", "mission"),
        ),
        "heart_rate": MetricDefinition(
            domain="physiological",
            measurement_kind="numeric",
            canonical_unit="bpm",
            minimum=0,
            scopes=("astronaut",),
        ),
        "ambient_pressure": MetricDefinition(
            domain="environmental",
            measurement_kind="numeric",
            canonical_unit="Pa",
            minimum=0,
            scopes=("spacecraft", "compartment"),
        ),
        "absorbed_dose": MetricDefinition(
            domain="radiation",
            measurement_kind="numeric",
            canonical_unit="Gy",
            minimum=0,
            scopes=("astronaut", "spacecraft", "compartment"),
        ),
        "sleep_state": MetricDefinition(
            domain="behavioral",
            measurement_kind="categorical",
            categories=("awake", "asleep"),
            scopes=("astronaut",),
        ),
        "gravity_magnitude": MetricDefinition(
            domain="altered_gravity",
            measurement_kind="numeric",
            canonical_unit="m/s2",
            minimum=0,
            scopes=("astronaut", "spacecraft", "compartment"),
        ),
        "exercise_active": MetricDefinition(
            domain="mission_context",
            measurement_kind="boolean",
            scopes=("astronaut", "mission"),
        ),
    }
)


class Observation(Contract):
    schema_version: Literal["1.0.0"]
    observation_id: Identifier
    timestamp: AwareDatetime
    ingested_at: AwareDatetime | None = None
    domain: Domain
    metric: Identifier
    scope: Scope
    measurement: Measurement
    provenance: Provenance
    quality: DataQuality

    @field_validator("timestamp", "ingested_at", mode="before")
    @classmethod
    def reject_numeric_time(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError(
                "timestamps must be timezone-aware datetime or ISO 8601 text"
            )
        return value

    @field_validator("timestamp", "ingested_at")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.fold:
                raise ValueError(
                    "ambiguous folded local time requires explicit UTC resolution"
                )
            return value.astimezone(UTC)
        return None

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        if self.ingested_at is not None and self.ingested_at < self.timestamp:
            raise ValueError(
                "ingestion precedes event time; resolve clock metadata explicitly"
            )
        definition = METRIC_REGISTRY.get(self.metric)
        if definition is None:
            raise ValueError("unsupported metric identifier")
        if definition.domain != self.domain:
            raise ValueError("metric is incompatible with observation domain")
        if self.scope.kind not in definition.scopes:
            raise ValueError("metric is incompatible with observation scope")
        if self.observation_id in self.provenance.parent_observation_ids:
            raise ValueError("observation cannot reference itself as a parent")
        absent = isinstance(self.measurement, UnavailableMeasurement)
        if absent != (self.quality.status in {"missing", "unavailable"}):
            raise ValueError(
                "absent measurement requires missing or unavailable quality"
            )
        if isinstance(self.measurement, UnavailableMeasurement):
            expected = (
                "missing"
                if self.measurement.reason == "not_received"
                else "unavailable"
            )
            if self.quality.status != expected:
                raise ValueError("absence reason is incompatible with quality status")
            return self
        if self.measurement.kind != definition.measurement_kind:
            raise ValueError("measurement kind is incompatible with metric")
        if isinstance(self.measurement, NumericMeasurement):
            if self.measurement.unit != definition.canonical_unit:
                raise ValueError(
                    "metric requires its canonical unit; no implicit conversion"
                )
        if isinstance(self.measurement, CategoricalMeasurement):
            if self.measurement.value not in definition.categories:
                raise ValueError("unsupported categorical state")
        return self
