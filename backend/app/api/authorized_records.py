"""Separate authenticated records API; anonymous research never reads these rows."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.application.authorized_records import (
    AccessDenied,
    AuthorizedRecords,
    Principal,
    StorageUnavailable,
)
from app.schemas.observation import Identifier, Observation


class MissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: Identifier


def build_authorized_router(
    service: AuthorizedRecords | None, clock: Callable[[], datetime]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/account", tags=["authenticated records"])

    def principal(authorization: str | None) -> Principal:
        if service is None:
            raise HTTPException(503)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401)
        try:
            return service.authenticate(authorization[7:])
        except AccessDenied as exc:
            raise HTTPException(403) from exc
        except StorageUnavailable as exc:
            raise HTTPException(503) from exc

    @router.get("/me")
    def me(authorization: Annotated[str | None, Header()] = None) -> Principal:
        return principal(authorization)

    @router.get("/observations")
    def read(
        mission_id: Annotated[Identifier, Query()],
        astronaut_id: Annotated[Identifier, Query()],
        authorization: Annotated[str | None, Header()] = None,
    ) -> tuple[Observation, ...]:
        actor = principal(authorization)
        assert service is not None
        try:
            return service.read(actor, mission_id, astronaut_id, clock())
        except AccessDenied as exc:
            raise HTTPException(403) from exc
        except StorageUnavailable as exc:
            raise HTTPException(503) from exc

    @router.post("/observations", status_code=201)
    def write(
        observation: Observation, authorization: Annotated[str | None, Header()] = None
    ) -> dict[str, str]:
        actor = principal(authorization)
        assert service is not None
        try:
            service.write(actor, observation, clock())
        except AccessDenied as exc:
            raise HTTPException(403) from exc
        except StorageUnavailable as exc:
            raise HTTPException(503) from exc
        return {"status": "persisted", "observation_id": observation.observation_id}

    @router.post("/missions", status_code=201)
    def mission(
        body: MissionInput, authorization: Annotated[str | None, Header()] = None
    ) -> dict[str, str]:
        actor = principal(authorization)
        assert service is not None
        try:
            service.create_mission(actor, body.mission_id)
        except AccessDenied as exc:
            raise HTTPException(403) from exc
        except StorageUnavailable as exc:
            raise HTTPException(503) from exc
        return {"mission_id": body.mission_id}

    return router
