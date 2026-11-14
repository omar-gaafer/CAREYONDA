"""Loopback-only real historical replay composition; no inference on import."""

import logging
import os
import platform
from pathlib import Path

from fastapi import FastAPI

from app.demo_main import create_app as create_demo_app
from app.model_a_main import ModelAConfig

MODEL_A_SHA256 = "f6b28b9d2e5925d0a568eba79bb0d3af516e31a8cbc7d96725ef86dfd85c44b6"
DATASET_SHA256 = "40005d13160fdf2ea729237f965508fd2864ac1e187a3dcf8753f7cdf928706b"


def create_app() -> FastAPI:
    """Use only explicitly trusted, separately provisioned server-side assets.

    Invalid/incomplete configuration keeps Model A unavailable; no fixture fallback.
    Existing RequestGuard continues to reject public hosts and non-loopback origins.
    """
    names = (
        "CAREYONDA_MODEL_A_ARTIFACT",
        "CAREYONDA_NASA_DATASET",
        "CAREYONDA_REPLAY_RECEIPT_DIR",
    )
    if os.environ.get("CAREYONDA_TRUSTED_LOCAL_MODEL_A") != "1" or not all(
        os.environ.get(n) for n in names
    ):
        return create_demo_app()
    try:
        import joblib  # type: ignore[import-untyped]  # Existing pinned dependency lacks stubs.
        import numpy
        import sklearn  # type: ignore[import-untyped]  # Existing pinned dependency lacks stubs.

        from app.storage.nasa_environment_model_store import read_metadata, sha256_file
        from app.storage.nasa_replay_catalog import acquire_replay_catalog

        if (
            platform.python_version(),
            numpy.__version__,
            sklearn.__version__,
            joblib.__version__,
        ) != ("3.12.10", "2.4.6", "1.9.1", "1.6.0"):
            raise ValueError("trusted artifact runtime mismatch")
        artifact = Path(os.environ[names[0]])
        if (artifact / "model.joblib").is_symlink() or sha256_file(
            artifact / "model.joblib"
        ) != MODEL_A_SHA256:
            raise ValueError("trusted artifact digest mismatch")
        metadata = read_metadata(artifact)
        if (
            metadata.artifact_sha256 != MODEL_A_SHA256
            or metadata.dataset.manifest_sha256 != DATASET_SHA256
        ):
            raise ValueError("trusted metadata mismatch")
        samples, receipt = acquire_replay_catalog(
            Path(os.environ[names[1]]),
            expected_manifest_sha256=DATASET_SHA256,
            receipt_directory=Path(os.environ[names[2]]),
        )
        config = ModelAConfig(
            artifact_directory=artifact,
            authorized_samples=samples,
            replay_receipt_files=(receipt,),
        )
    except (ImportError, OSError, ValueError, KeyError):
        logging.getLogger(__name__).warning(
            "Model A unavailable: local trusted replay preflight failed"
        )
        return create_demo_app()
    return create_demo_app(config)
