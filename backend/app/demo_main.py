"""Local demo composition; optional Model A plus transient Model C and synthetic M2."""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from app.api.contracts import Capability
from app.api.model_c import build_model_c_router
from app.application.environmental_api import ModelABinding
from app.model_a_main import ModelAConfig, _load_model
from app.model_a_main import create_app as create_model_a_app


def create_app(
    config: ModelAConfig | None = None,
    *,
    model_loader: Callable[[ModelAConfig], ModelABinding] = _load_model,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    app = create_model_a_app(
        config,
        model_loader=model_loader,
        clock=clock,
        additional_capabilities=(
            Capability(
                name="model_c_transient_sleep_fatigue_research",
                availability="available",
            ),
        ),
    )
    app.include_router(build_model_c_router(clock))
    return app
