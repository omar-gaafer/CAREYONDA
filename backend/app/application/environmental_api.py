"""Server-authorized provenance boundary for optional Model A HTTP assessments."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.schemas.environmental_anomaly_context import (
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
    ReplayAcquisition,
)

ModelAvailability = Literal["available", "unavailable", "incompatible"]


class EnvironmentalInference(Protocol):
    def assess(
        self, samples: Sequence[EnvironmentalSample], *, assessed_at: datetime
    ) -> tuple[EnvironmentalAnomalyContext, ...]: ...


@dataclass(frozen=True)
class ModelABinding:
    availability: ModelAvailability = "unavailable"
    service: EnvironmentalInference | None = None

    def __post_init__(self) -> None:
        if (self.availability == "available") != (self.service is not None):
            raise ValueError("model availability and service disagree")


class ProvenanceNotAuthorized(ValueError):
    """Client claims do not match independently provisioned server evidence."""


class EnvironmentalApiInputError(ValueError):
    """Invalid assessment time or unavailable evidence; no values in messages."""


class AuthorizedEnvironmentalInference:
    def __init__(self, clock: Callable[[], datetime]) -> None:
        self.clock = clock
        self.binding = ModelABinding()
        self._samples: dict[tuple[str, str], EnvironmentalSample] = {}

    def initialize(
        self,
        binding: ModelABinding,
        samples: tuple[EnvironmentalSample, ...],
        receipts: tuple[ReplayAcquisition, ...],
    ) -> None:
        catalog: dict[tuple[str, str], EnvironmentalSample] = {}
        for sample in samples:
            validated = EnvironmentalSample.model_validate(sample.model_dump())
            key = (validated.sample_id, validated.assessment_mode)
            if key in catalog:
                raise ValueError("duplicate authorized sample identity")
            if (
                validated.assessment_mode == "historical_replay"
                and validated.replay_acquisition not in receipts
            ):
                raise ValueError("replay receipt is not server verified")
            catalog[key] = validated
        self._samples = catalog
        self.binding = binding

    def authorized_samples(self) -> tuple[EnvironmentalSample, ...]:
        return tuple(self._samples.values())

    def resolve(
        self, references: tuple[tuple[str, str], ...]
    ) -> tuple[EnvironmentalSample, ...]:
        try:
            return tuple(self._samples[reference] for reference in references)
        except KeyError as exc:
            raise ProvenanceNotAuthorized("sample reference is not authorized") from exc

    def close(self) -> None:
        self._samples = {}
        self.binding = ModelABinding()

    def assess(
        self, samples: tuple[EnvironmentalSample, ...], *, assessed_at: datetime
    ) -> tuple[EnvironmentalAnomalyContext, ...]:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None or assessed_at > now:
            raise EnvironmentalApiInputError("assessment time is not server-verifiable")
        trusted = []
        for sample in samples:
            authorized = self._samples.get((sample.sample_id, sample.assessment_mode))
            if authorized is None or authorized != sample:
                raise ProvenanceNotAuthorized("sample is not authorized")
            trusted.append(authorized)
        if self.binding.service is None:
            raise EnvironmentalApiInputError("model unavailable")
        try:
            return self.binding.service.assess(trusted, assessed_at=assessed_at)
        except ValueError as exc:
            raise EnvironmentalApiInputError(
                "invalid environmental assessment"
            ) from exc
