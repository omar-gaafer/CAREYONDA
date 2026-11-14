"""Explicit trusted v1 artifact compatibility; no fitting, repackaging or defaults."""

from __future__ import annotations

import io
import json
import platform
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal

import joblib  # type: ignore[import-untyped]  # pinned package has no py.typed
import numpy as np
from pydantic import Field, model_validator
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from app.features.temporal_features import feature_schema
from app.schemas.baseline import Ids
from app.schemas.model_b import (
    FEATURE_ORDER,
    FEATURE_UNITS,
    Digest,
    Finite,
    ModelBMetadata,
    ThresholdPolicy,
    VerifiedModelB,
)
from app.schemas.observation import Contract
from app.storage.model_b_store import ModelBArtifactError, verify_model_b_artifact


class V1Policy(Contract):
    """Research settings. Quantile must be explicitly chosen before evaluation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    random_state: Annotated[int, Field(strict=True, ge=0)] = 42
    n_estimators: Annotated[int, Field(strict=True, gt=0)] = 200
    max_samples: Annotated[int, Field(strict=True, gt=0)] = 256
    baseline_quantile: Annotated[Finite, Field(gt=0, lt=1)]
    threshold_method: Literal["training_baseline_quantile_higher"] = (
        "training_baseline_quantile_higher"
    )
    comparison: Literal["greater_than"] = "greater_than"
    fold_count: Annotated[int, Field(strict=True, ge=2)] = 4


class V1Metadata(Contract):
    schema_version: Literal["1.0.0"]
    model_id: Literal["model-b-synthetic-isolation-forest"]
    model_version: Literal["1.0.0"]
    interpretation: Literal["synthetic_research_only"]
    feature_order: tuple[str, ...]
    feature_units: tuple[str, ...]
    policy: V1Policy
    threshold: Finite
    score_definition: Literal["negative_sklearn_score_samples"]
    score_direction: Literal["higher_is_more_anomalous"]
    threshold_comparison: Literal["greater_than"]
    dataset_manifest_sha256: Digest
    training_episode_ids: Ids
    training_sample_ids: Ids
    imputation_medians: tuple[Finite, ...]
    descriptive_training_means: tuple[Finite, ...]
    descriptive_training_stds: tuple[Finite, ...]
    runtime_versions: dict[str, str]
    source_code_sha256: dict[str, Digest]
    preprocessing: Literal["median_training_only_no_scaling"]
    effective_max_samples: int = Field(gt=0)

    @model_validator(mode="after")
    def shape(self) -> V1Metadata:
        if self.feature_order != FEATURE_ORDER or self.feature_units != FEATURE_UNITS:
            raise ValueError("artifact feature order/units differ from Model B")
        if any(
            len(values) != 16
            for values in (
                self.imputation_medians,
                self.descriptive_training_means,
                self.descriptive_training_stds,
            )
        ):
            raise ValueError(
                "artifact preprocessing/statistics must preserve sixteen columns"
            )
        if (
            not self.training_episode_ids
            or not self.training_sample_ids
            or any(v < 0 for v in self.descriptive_training_stds)
        ):
            raise ValueError(
                "artifact lacks training lineage or has negative dispersion"
            )
        if self.effective_max_samples != min(
            self.policy.max_samples, len(self.training_sample_ids)
        ):
            raise ValueError(
                "effective estimator sample count contradicts training lineage"
            )
        return self


PIPELINE_FILE = "model_b_pipeline.joblib"
FILES = (
    PIPELINE_FILE,
    "metadata.json",
    "feature_schema.json",
    "evaluation.json",
    "predictions.csv",
)


class ArtifactManifest(Contract):
    schema_version: Literal["1.0.0"]
    files: dict[str, Digest]


def runtime_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        **{
            name: version(name) for name in ("numpy", "scipy", "scikit-learn", "joblib")
        },
    }


class FittedScorer:
    """Canonical service already imputes; call the original forest exactly once."""

    def __init__(self, pipeline: Pipeline) -> None:
        self._pipeline = pipeline

    def score_samples(self, values: Sequence[Sequence[float]]) -> Sequence[float]:
        result = np.asarray(
            self._pipeline.named_steps["model"].score_samples(
                np.asarray(values, dtype=np.float64)
            ),
            dtype=np.float64,
        )
        return [float(v) for v in result]

    def score_raw_samples(
        self, values: Sequence[Sequence[float | None]]
    ) -> tuple[float, ...]:
        """Verification path through the unmodified fitted imputer AND estimator."""
        raw = np.asarray(
            [[np.nan if v is None else v for v in row] for row in values],
            dtype=np.float64,
        )
        return tuple(float(v) for v in self._pipeline.score_samples(raw))


@dataclass(frozen=True)
class LoadedModelB:
    model: VerifiedModelB
    scorer: FittedScorer
    experimental_policy: ThresholdPolicy
    original_metadata_sha256: str
    original_manifest_sha256: str
    training_sample_ids: tuple[str, ...]
    training_episode_ids: tuple[str, ...]
    evaluation_bytes: bytes


def load_trusted_model_b_v1(
    directory: Path,
    *,
    trusted_local_artifact: bool = False,
    expected_artifact_sha256: str,
    expected_manifest_sha256: str,
) -> LoadedModelB:
    """Caller owns trust authorization and pins. Never accepts transport paths.

    All files are read once and hash/schema/runtime checked before deserialization.
    The original bundle remains untouched; v2 metadata exists only in memory.
    """
    if trusted_local_artifact is not True:
        raise ModelBArtifactError("trusted-local opt-in required")
    if directory.is_symlink() or not directory.is_dir():
        raise ModelBArtifactError("artifact directory unavailable or linked")

    def read(name: str) -> bytes:
        p = directory / name
        if p.is_symlink() or not p.is_file() or p.stat().st_size > 64 * 1024 * 1024:
            raise ModelBArtifactError("artifact file unavailable, linked or oversized")
        return p.read_bytes()

    manifest_bytes = read("artifact_manifest.json")
    if sha256(manifest_bytes).hexdigest() != expected_manifest_sha256:
        raise ModelBArtifactError("manifest pin mismatch")
    manifest = ArtifactManifest.model_validate_json(manifest_bytes)
    if set(manifest.files) != set(FILES):
        raise ModelBArtifactError("artifact file set mismatch")
    raw = {name: read(name) for name in FILES}
    if any(sha256(raw[name]).hexdigest() != manifest.files[name] for name in FILES):
        raise ModelBArtifactError("artifact manifest integrity mismatch")
    if sha256(raw[PIPELINE_FILE]).hexdigest() != expected_artifact_sha256:
        raise ModelBArtifactError("artifact pin mismatch")
    metadata = V1Metadata.model_validate_json(raw["metadata.json"])
    if (
        metadata.model_version != "1.0.0"
        or metadata.model_id != "model-b-synthetic-isolation-forest"
    ):
        raise ModelBArtifactError("model identity mismatch")
    if metadata.runtime_versions != runtime_versions():
        raise ModelBArtifactError("artifact runtime mismatch")
    if json.loads(raw["feature_schema.json"]) != feature_schema(300):
        raise ModelBArtifactError("artifact feature schema mismatch")
    if metadata.policy.baseline_quantile != 0.95:
        raise ModelBArtifactError("compatibility supports recorded q95 only")
    params: dict[str, str | int | float | bool] = {
        "n_estimators": metadata.policy.n_estimators,
        "max_samples": metadata.effective_max_samples,
        "random_state": metadata.policy.random_state,
        "max_features": 1.0,
        "bootstrap": False,
        "contamination": "auto",
        "n_jobs": 1,
    }
    v2 = ModelBMetadata(
        model_version=metadata.model_version,
        artifact_sha256=expected_artifact_sha256,
        training_manifest_sha256=metadata.dataset_manifest_sha256,
        feature_order=metadata.feature_order,
        units=metadata.feature_units,
        imputation_medians=metadata.imputation_medians,
        runtime_versions=metadata.runtime_versions,
        estimator_parameters=params,
    )
    converted = v2.model_dump_json().encode()
    verified = verify_model_b_artifact(
        metadata_bytes=converted,
        artifact_bytes=raw[PIPELINE_FILE],
        expected_metadata_sha256=sha256(converted).hexdigest(),
        expected_artifact_sha256=expected_artifact_sha256,
        trusted_local_artifact=True,
        runtime_versions=runtime_versions(),
    )
    # Only this explicit trusted path deserializes, from the already verified bytes.
    pipeline = joblib.load(io.BytesIO(raw[PIPELINE_FILE]))
    if not isinstance(pipeline, Pipeline) or tuple(pipeline.named_steps) != (
        "imputer",
        "model",
    ):
        raise ModelBArtifactError("fitted pipeline shape mismatch")
    imputer, estimator = pipeline.named_steps["imputer"], pipeline.named_steps["model"]
    if not isinstance(imputer, SimpleImputer) or not isinstance(
        estimator, IsolationForest
    ):
        raise ModelBArtifactError("fitted estimator type mismatch")
    if (
        imputer.n_features_in_ != 16
        or estimator.n_features_in_ != 16
        or imputer.strategy != "median"
        or not imputer.keep_empty_features
        or tuple(float(v) for v in imputer.statistics_) != metadata.imputation_medians
        or any(estimator.get_params()[k] != v for k, v in params.items())
        or len(estimator.estimators_) != metadata.policy.n_estimators
    ):
        raise ModelBArtifactError("fitted preprocessing or parameters mismatch")
    policy = ThresholdPolicy(
        policy_id="recorded-v1-training-q95",
        model_artifact_sha256=expected_artifact_sha256,
        derivation_manifest_sha256=expected_manifest_sha256,
        method="local_training_quantile",
        threshold=metadata.threshold,
        comparison="greater_than",
        quantile=metadata.policy.baseline_quantile,
        derivation_reference="Original verified v1 metadata; training baseline NumPy higher quantile; not canonical approval",
        approval_reference=None,
    )
    return LoadedModelB(
        verified,
        FittedScorer(pipeline),
        policy,
        sha256(raw["metadata.json"]).hexdigest(),
        expected_manifest_sha256,
        metadata.training_sample_ids,
        metadata.training_episode_ids,
        raw["evaluation.json"],
    )
