"""Opt-in local synthetic viewer; no authenticated health repository access."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.application.authorized_records import StorageUnavailable
from app.application.synthetic_viewer import SyntheticReadSource
from app.schemas.observation import METRIC_REGISTRY, Identifier
from app.schemas.synthetic_viewer import SyntheticCatalog, SyntheticPage


def build_synthetic_router(viewer: SyntheticReadSource | None) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/local-synthetic", tags=["local synthetic database"]
    )

    @router.get("/catalog", response_model=SyntheticCatalog)
    def catalog() -> SyntheticCatalog:
        if viewer is None:
            raise HTTPException(503)
        try:
            return viewer.catalog()
        except (StorageUnavailable, ValueError) as exc:
            raise HTTPException(503) from exc

    @router.get("/observations", response_model=SyntheticPage)
    def observations(
        mission_id: Annotated[Identifier, Query()],
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0, le=2000)] = 0,
        metric: Annotated[Identifier | None, Query()] = None,
        source_id: Annotated[Identifier | None, Query()] = None,
    ) -> SyntheticPage:
        if viewer is None:
            raise HTTPException(503)
        if metric is not None and metric not in METRIC_REGISTRY:
            raise HTTPException(422)
        try:
            return viewer.page(mission_id, limit, offset, metric, source_id)
        except ValueError as exc:
            raise HTTPException(422) from exc
        except StorageUnavailable as exc:
            raise HTTPException(503) from exc

    return router
