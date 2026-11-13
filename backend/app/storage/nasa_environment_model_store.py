"""Local filesystem persistence for the Model A artifact (infrastructure adapter).

The estimator is stored with joblib (pickle-based). Unpickling can execute code,
so ``load_model_a`` verifies the artifact SHA-256 recorded in ``metadata.json``
before deserializing, and the runtime scikit-learn version must exactly match the
training version. Only load artifacts produced locally by the training entry point.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib  # type: ignore[import-untyped]  # joblib ships no type information
import sklearn  # type: ignore[import-untyped]  # scikit-learn ships no py.typed
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

from app.ai.nasa_environment_anomaly import (
    ModelProvenance,
    NasaEnvironmentAnomalyDetector,
    ScoringEstimator,
    feature_names,
)
from app.schemas.nasa_environment_model import ModelAMetadata

ARTIFACT_FILE = "model.joblib"
METADATA_FILE = "metadata.json"


class ModelArtifactError(RuntimeError):
    """The stored artifact is missing, altered, or incompatible with this runtime."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_estimator(directory: Path, estimator: ScoringEstimator) -> str:
    """Write the estimator into a new directory and return its SHA-256."""
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / ARTIFACT_FILE
    joblib.dump(estimator, path, compress=3)
    return sha256_file(path)


def write_metadata(directory: Path, metadata: ModelAMetadata) -> None:
    if sha256_file(directory / metadata.artifact_file) != metadata.artifact_sha256:
        raise ModelArtifactError("metadata hash does not match the written artifact")
    payload = json.loads(metadata.model_dump_json())
    (directory / METADATA_FILE).write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_metadata(directory: Path) -> ModelAMetadata:
    path = directory / METADATA_FILE
    if not path.is_file():
        raise ModelArtifactError("metadata.json not found")
    return ModelAMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def provenance_from(metadata: ModelAMetadata) -> ModelProvenance:
    return ModelProvenance(
        model_id=metadata.model_id,
        model_version=metadata.model_version,
        artifact_sha256=metadata.artifact_sha256,
        feature_schema_version=metadata.dataset.schema_version,
        dataset_manifest_sha256=metadata.dataset.manifest_sha256,
        threshold_method=None
        if metadata.threshold is None
        else metadata.threshold.method,
    )


def load_model_a(directory: Path) -> NasaEnvironmentAnomalyDetector:
    """Verify integrity and compatibility, then build the inference detector."""
    metadata = read_metadata(directory)
    if metadata.preprocessing.feature_names != feature_names():
        raise ModelArtifactError("artifact feature contract differs from schema")
    trained_with = metadata.estimator.runtime_versions.get("scikit-learn")
    if trained_with != sklearn.__version__:
        raise ModelArtifactError(
            "scikit-learn version differs from the training runtime; "
            "install the pinned version instead of loading across versions"
        )
    artifact = directory / metadata.artifact_file
    if artifact.name != metadata.artifact_file or not artifact.is_file():
        raise ModelArtifactError("artifact file not found")
    if sha256_file(artifact) != metadata.artifact_sha256:
        raise ModelArtifactError("artifact SHA-256 does not match metadata")
    estimator = joblib.load(artifact)
    if not isinstance(estimator, IsolationForest):
        raise ModelArtifactError("artifact is not an IsolationForest")
    if getattr(estimator, "n_features_in_", None) != len(feature_names()):
        raise ModelArtifactError("estimator feature count differs from schema")
    return NasaEnvironmentAnomalyDetector(
        estimator=estimator,
        preprocessing=metadata.preprocessing,
        threshold=metadata.threshold,
        provenance=provenance_from(metadata),
    )
