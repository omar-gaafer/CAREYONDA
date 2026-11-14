"""Local API composition root; use uvicorn app.main:create_app --factory."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.ai.hazard_reasoning import ReasoningInputError
from app.api.contracts import Capability
from app.api.routes import build_router
from app.api.security import ALLOWED_ORIGINS, RequestGuard, error_response
from app.application.evidence import ContextUnavailable, EvidenceSource
from app.storage.local_evidence import LocalSyntheticSource


def create_app(
    source: EvidenceSource | None = None,
    *,
    capability_overrides: Callable[[], tuple[Capability, ...]] | None = None,
) -> FastAPI:
    configured = (
        source
        if source is not None
        else LocalSyntheticSource(
            Path(__file__).parent / "storage" / "fixtures" / "api_evidence.json"
        )
    )
    if any(
        o.provenance.origin != "simulated"
        for p in configured.presets()
        for o in p.observations
    ):
        raise ValueError("Only synthetic sources are supported by this API version")
    app = FastAPI(
        title="CAREYONDA local research API",
        telemetry={
            "tracing": False,
            "metrics": False,
            "logs": False,
            "operation_spans": False,
            "auto_configure": False,
        },
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
    )
    app.include_router(build_router(configured, capability_overrides))

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return error_response("invalid_request", request.state.correlation_id, 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        # Detail is never reflected; it could originate from a sensitive adapter.
        return error_response(
            f"http_{error.status_code}", request.state.correlation_id, error.status_code
        )

    @app.exception_handler(ContextUnavailable)
    async def context_error(
        request: Request, error: ContextUnavailable
    ) -> JSONResponse:
        return error_response("context_not_allowed", request.state.correlation_id, 403)

    @app.exception_handler(ReasoningInputError)
    async def reasoning_error(
        request: Request, error: ReasoningInputError
    ) -> JSONResponse:
        return error_response(
            "invalid_reasoning_window", request.state.correlation_id, 422
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Correlation-ID"],
        allow_credentials=False,
    )
    app.add_middleware(RequestGuard)
    return app
