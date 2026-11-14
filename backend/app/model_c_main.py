"""Optional Model C composition root; the base synthetic-only app stays unchanged.

Run locally: ``uvicorn app.model_c_main:create_app --factory --host 127.0.0.1``.
Adds ``POST /api/v1/model-c/local-assessments`` for transient, self-reported
entries. No database, file, cache, telemetry or external service is used.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from app.api.model_c import build_model_c_router
from app.main import create_app as create_base_app


def create_app(*, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> FastAPI:
    app = create_base_app()
    app.include_router(build_model_c_router(clock))
    return app
