"""HTTP transport only: contract parsing and injected application calls."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import AwareDatetime

from app.api.contracts import (
    CapabilitiesResponse,
    Capability,
    ContextPreset,
    ContextsResponse,
    ErrorResponse,
    HealthResponse,
    InvestigationRequest,
    InvestigationResponse,
    ObservationPage,
)
from app.application.evidence import EvidenceSource, InvestigationService
from app.schemas.observation import METRIC_REGISTRY, Identifier, Observation


def build_router(source: EvidenceSource) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 403, 404, 413, 414, 415, 422, 500)
        },
    )
    service = InvestigationService(source)
    records = tuple(
        sorted(
            (o for p in source.presets() for o in p.observations),
            key=lambda o: (o.timestamp, o.observation_id),
        )
    )
    subjects = {p.current.astronaut_id for p in source.presets()}
    missions = {p.current.mission_id for p in source.presets()}

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @router.get("/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            capabilities=(
                Capability(
                    name="observation_contract_validation", availability="available"
                ),
                Capability(name="observations", availability="simulation_only"),
                Capability(name="m2_reasoning", availability="simulation_only"),
                Capability(name="safety_policies", availability="not_implemented"),
                Capability(name="trained_models", availability="not_implemented"),
                Capability(
                    name="investigation_persistence", availability="not_implemented"
                ),
            )
        )

    @router.get("/contexts", response_model=ContextsResponse)
    def contexts() -> ContextsResponse:
        return ContextsResponse(
            presets=tuple(
                ContextPreset(title=p.title, current=p.current, reference=p.reference)
                for p in source.presets()
            )
        )

    @router.get("/observations", response_model=ObservationPage)
    def observations(
        mission_id: Annotated[Identifier | None, Query()] = None,
        astronaut_id: Annotated[Identifier | None, Query()] = None,
        metric: Annotated[Identifier | None, Query()] = None,
        start: Annotated[AwareDatetime | None, Query()] = None,
        end: Annotated[AwareDatetime | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    ) -> ObservationPage:
        if (mission_id is not None and mission_id not in missions) or (
            astronaut_id is not None and astronaut_id not in subjects
        ):
            raise HTTPException(403, "context_not_allowed")
        if metric is not None and metric not in METRIC_REGISTRY:
            raise HTTPException(422, "unsupported_metric")
        if start is not None and end is not None and start > end:
            raise HTTPException(422, "invalid_time_window")

        def matches(o: Observation) -> bool:
            return (
                (mission_id is None or o.scope.mission_id == mission_id)
                and (
                    astronaut_id is None
                    or (
                        o.scope.kind == "astronaut"
                        and o.scope.astronaut_id == astronaut_id
                    )
                )
                and (metric is None or o.metric == metric)
                and (start is None or o.timestamp >= start)
                and (end is None or o.timestamp <= end)
            )

        selected = tuple(o for o in records if matches(o))
        return ObservationPage(
            items=selected[offset : offset + limit],
            total=len(selected),
            limit=limit,
            offset=offset,
        )

    @router.get("/observations/{observation_id}", response_model=Observation)
    def observation(observation_id: Annotated[Identifier, Path()]) -> Observation:
        row = next((o for o in records if o.observation_id == observation_id), None)
        if row is None:
            raise HTTPException(404, "evidence_not_found")
        return row

    @router.post("/investigations", response_model=InvestigationResponse)
    def investigation(payload: InvestigationRequest) -> InvestigationResponse:
        return InvestigationResponse(
            result=service.run(
                payload.current, payload.reference, payload.window_seconds
            )
        )

    return router
