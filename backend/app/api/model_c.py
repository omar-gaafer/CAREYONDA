"""Model C local-entry transport: validate, assess, return. Nothing is retained.

Request bodies are bounded by ``RequestGuard`` (16 KiB, JSON only, loopback host).
Entry values are never logged or echoed in errors; errors carry a code and the
server correlation ID only.
"""

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from app.ai.isolation_confinement import ModelCInputError
from app.api.contracts import ErrorResponse
from app.api.security import error_response
from app.application.model_c_local import (
    TIME_CONVENTION,
    LocalEntryError,
    assess_local_submission,
)
from app.schemas.model_c_local_entry import ModelCLocalResponse, ModelCLocalSubmission


def build_model_c_router(clock: Callable[[], datetime]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/model-c")

    @router.post(
        "/local-assessments",
        response_model=ModelCLocalResponse,
        responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    def assess(
        payload: ModelCLocalSubmission, request: Request
    ) -> ModelCLocalResponse | JSONResponse:
        correlation: str = request.state.correlation_id
        try:
            result = assess_local_submission(payload, clock())
        except LocalEntryError as error:
            return error_response(error.code, correlation, 422)
        except ModelCInputError:
            return error_response("model_c_input_rejected", correlation, 422)
        return ModelCLocalResponse(
            correlation_id=correlation,
            time_convention=TIME_CONVENTION,
            result=result,
        )

    return router
