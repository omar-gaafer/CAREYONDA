"""Versioned HTTP-only request/response contracts, distinct from domain results."""

from typing import Literal

from pydantic import Field

from app.features.temporal_features import SampleAnchor
from app.schemas.investigation import Investigation
from app.schemas.observation import Contract, Observation


class HealthResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["ok"] = "ok"
    source: Literal["configured_synthetic"] = "configured_synthetic"


class Capability(Contract):
    name: str
    availability: Literal[
        "available", "simulation_only", "not_implemented", "unavailable"
    ]
    medically_validated: Literal[False] = False


class CapabilitiesResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    capabilities: tuple[Capability, ...]
    authentication: Literal["none_local_only"] = "none_local_only"


class ContextPreset(Contract):
    title: str
    current: SampleAnchor
    reference: SampleAnchor


class ContextsResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    source: Literal["configured_synthetic"] = "configured_synthetic"
    presets: tuple[ContextPreset, ...]


class ObservationPage(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    source: Literal["configured_synthetic"] = "configured_synthetic"
    items: tuple[Observation, ...]
    total: int
    limit: int
    offset: int


class InvestigationRequest(Contract):
    schema_version: Literal["1.0.0"]
    current: SampleAnchor
    reference: SampleAnchor
    window_seconds: int = Field(default=300, strict=True, gt=0, le=3600)


class InvestigationResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    source: Literal["configured_synthetic"] = "configured_synthetic"
    result: Investigation


class ErrorDetail(Contract):
    code: str
    correlation_id: str


class ErrorResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    error: ErrorDetail
