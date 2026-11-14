"""Bounded Model A transport. No client-controlled artifact or receipt loading."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from starlette.responses import JSONResponse

from app.api.contracts import ErrorResponse
from app.api.security import error_response
from app.application.environmental_api import (
    AuthorizedEnvironmentalInference,
    EnvironmentalApiInputError,
    ModelAvailability,
    ProvenanceNotAuthorized,
)
from app.schemas.environmental_anomaly_context import (
    LIMITATIONS,
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
    EnvironmentalScope,
    Time,
)
from app.schemas.observation import Contract, Identifier

MAX_BATCH = 2


class EnvironmentalAnomalyRequest(Contract):
    schema_version: Literal["1.0.0"]
    assessed_at: Time
    samples: Annotated[
        tuple[EnvironmentalSample, ...], Field(min_length=1, max_length=MAX_BATCH)
    ]


class AuthorizedSampleReference(Contract):
    sample_id: Identifier
    assessment_mode: Literal["live", "historical_replay"]


class EnvironmentalReferenceRequest(Contract):
    schema_version: Literal["1.1.0"]
    assessed_at: Time
    sample_references: Annotated[
        tuple[AuthorizedSampleReference, ...], Field(min_length=1, max_length=MAX_BATCH)
    ]


class AuthorizedSampleSummary(AuthorizedSampleReference):
    source_event_time: Time
    scope: EnvironmentalScope
    receipt_id: Identifier | None


class AuthorizedSamplesResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    correlation_id: Identifier
    model_availability: ModelAvailability
    samples: tuple[AuthorizedSampleSummary, ...]


class EnvironmentalAnomalyResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    correlation_id: Identifier
    model_availability: ModelAvailability
    contexts: tuple[EnvironmentalAnomalyContext, ...]
    limitations: tuple[str, ...] = LIMITATIONS


def build_environmental_router(gateway: AuthorizedEnvironmentalInference) -> APIRouter:
    router = APIRouter(prefix="/api/v1/environmental")

    def dependency() -> AuthorizedEnvironmentalInference:
        return gateway

    @router.get("/authorized-samples", response_model=AuthorizedSamplesResponse)
    def references(
        request: Request,
        authorized: Annotated[AuthorizedEnvironmentalInference, Depends(dependency)],
    ) -> AuthorizedSamplesResponse:
        return AuthorizedSamplesResponse(
            correlation_id=request.state.correlation_id,
            model_availability=authorized.binding.availability,
            samples=tuple(
                AuthorizedSampleSummary(
                    sample_id=s.sample_id,
                    assessment_mode=s.assessment_mode,
                    source_event_time=s.event_time_utc,
                    scope=s.scope,
                    receipt_id=s.replay_acquisition.record_id
                    if s.replay_acquisition
                    else None,
                )
                for s in authorized.authorized_samples()
            ),
        )

    @router.post(
        "/anomaly-context",
        response_model=EnvironmentalAnomalyResponse,
        responses={
            403: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": EnvironmentalAnomalyResponse},
        },
    )
    def assess(
        payload: EnvironmentalAnomalyRequest | EnvironmentalReferenceRequest,
        request: Request,
        authorized: Annotated[AuthorizedEnvironmentalInference, Depends(dependency)],
    ) -> EnvironmentalAnomalyResponse | JSONResponse:
        correlation = request.state.correlation_id
        availability = authorized.binding.availability
        if availability != "available":
            body = EnvironmentalAnomalyResponse(
                correlation_id=correlation,
                model_availability=availability,
                contexts=(),
                limitations=(
                    *LIMITATIONS,
                    "Model unavailable: no sample accepted or scored; no fallback inference.",
                ),
            )
            return JSONResponse(body.model_dump(mode="json"), status_code=503)
        try:
            samples = (
                payload.samples
                if isinstance(payload, EnvironmentalAnomalyRequest)
                else authorized.resolve(
                    tuple(
                        (r.sample_id, r.assessment_mode)
                        for r in payload.sample_references
                    )
                )
            )
            contexts = authorized.assess(samples, assessed_at=payload.assessed_at)
        except ProvenanceNotAuthorized:
            return error_response(
                "environmental_provenance_not_authorized", correlation, 403
            )
        except EnvironmentalApiInputError:
            return error_response("invalid_environmental_assessment", correlation, 422)
        return EnvironmentalAnomalyResponse(
            correlation_id=correlation,
            model_availability=availability,
            contexts=contexts,
        )

    return router
