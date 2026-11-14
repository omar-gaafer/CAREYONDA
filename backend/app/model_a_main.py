"""Optional Model A composition root; existing M3 application stays unchanged."""

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI

from app.api.contracts import Capability
from app.api.environmental_anomaly import build_environmental_router
from app.application.environmental_api import (
    AuthorizedEnvironmentalInference,
    ModelABinding,
)
from app.main import create_app as create_base_app
from app.schemas.environmental_anomaly_context import (
    EnvironmentalSample,
    ReplayAcquisition,
)


@dataclass(frozen=True)
class ModelAConfig:
    """Trusted deployment inputs only; never populated from an HTTP request."""

    artifact_directory: Path | None = None
    authorized_samples: tuple[EnvironmentalSample, ...] = ()
    replay_receipt_files: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        if len(self.authorized_samples) > 128 or len(self.replay_receipt_files) > 32:
            raise ValueError("server catalog exceeds startup bounds")
        if any(len(sample.observations) > 128 for sample in self.authorized_samples):
            raise ValueError("authorized evidence history exceeds startup bounds")


def _load_model(config: ModelAConfig) -> ModelABinding:
    directory = config.artifact_directory
    if directory is None:
        return ModelABinding()
    if (
        not (directory / "metadata.json").is_file()
        or not (directory / "model.joblib").is_file()
    ):
        return ModelABinding()
    if (directory / "metadata.json").stat().st_size > 262144 or (
        directory / "model.joblib"
    ).stat().st_size > 64 * 1024 * 1024:
        return ModelABinding("incompatible")
    try:
        from app.application.environmental_anomaly import EnvironmentalAnomalyService
        from app.storage.nasa_environment_model_store import load_model_a, read_metadata

        metadata = read_metadata(directory)
        if (
            metadata.model_version != "1.1.0"
            or metadata.dataset.schema_version != "1.0.0"
        ):
            return ModelABinding("incompatible")
        return ModelABinding(
            "available", EnvironmentalAnomalyService(load_model_a(directory))
        )
    except ImportError:
        return ModelABinding()
    except Exception:
        return ModelABinding("incompatible")


def _read_receipts(files: tuple[Path, ...]) -> tuple[ReplayAcquisition, ...]:
    receipts = []
    for path in files:
        if path.stat().st_size > 16384:
            raise ValueError("receipt exceeds startup bounds")
        raw = json.loads(path.read_text(encoding="utf-8"))
        receipts.append(
            ReplayAcquisition.model_validate(
                {key: raw[key] for key in ReplayAcquisition.model_fields}
            )
        )
    if len({r.record_id for r in receipts}) != len(receipts):
        raise ValueError("duplicate server receipt identity")
    return tuple(receipts)


def create_app(
    config: ModelAConfig | None = None,
    *,
    additional_capabilities: tuple[Capability, ...] = (),
    model_loader: Callable[[ModelAConfig], ModelABinding] = _load_model,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    configured = config if config is not None else ModelAConfig()
    gateway = AuthorizedEnvironmentalInference(clock)

    def capabilities() -> tuple[Capability, ...]:
        return (
            Capability(
                name="trained_models",
                availability="available"
                if gateway.binding.availability == "available"
                else "unavailable",
            ),
            Capability(name="model_a_environmental_api", availability="available"),
            *additional_capabilities,
        )

    app = create_base_app(capability_overrides=capabilities)
    previous = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with previous(application):
            try:
                receipts = _read_receipts(configured.replay_receipt_files)
                gateway.initialize(
                    model_loader(configured), configured.authorized_samples, receipts
                )
            except Exception:
                gateway.close()
            try:
                yield
            finally:
                gateway.close()

    app.router.lifespan_context = lifespan
    app.include_router(build_environmental_router(gateway))
    return app
