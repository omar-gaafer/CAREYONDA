"""Versioned persisted contract for Model A (NASA RR-1 environment anomaly detector).

This module only describes metadata. It does not import model runtimes, storage, or
HTTP frameworks. Anomaly scores described here are unsupervised Isolation Forest
scores; they are not probabilities, clinical findings, or hazard thresholds.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MODEL_A_METADATA_VERSION: Final = "1.0.0"
MODEL_A_ID: Final = "careyonda-model-a-nasa-rr1-environment-iforest"

ParamValue = str | int | float | bool | None


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeatureContract(_Frozen):
    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    nullable: bool
    metric: str | None = None


class SplitFileRecord(_Frozen):
    file: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: int = Field(ge=0)
    start_utc: datetime | None = None
    end_utc: datetime | None = None


class DatasetProvenance(_Frozen):
    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    splits: dict[str, SplitFileRecord]


class PreprocessingSpec(_Frozen):
    """Train-only fitted preprocessing applied before scoring.

    ``impute_median`` maps structurally nullable features to their training-split
    median. ``abstain_if_missing`` lists features whose absence makes a row
    unscorable. ``training_constants`` lists non-indicator features that never
    varied in training; any other value is outside what the fitted trees can
    represent. ``*_missing`` indicators are excluded: inference validates them
    against value presence and a set indicator abstains via its missing value.
    """

    feature_names: tuple[str, ...] = Field(min_length=1)
    impute_median: dict[str, float]
    abstain_if_missing: tuple[str, ...]
    training_constants: dict[str, float]
    method: str = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> PreprocessingSpec:
        names = set(self.feature_names)
        if len(names) != len(self.feature_names):
            raise ValueError("feature_names must be unique")
        referenced = (
            set(self.impute_median)
            | set(self.abstain_if_missing)
            | set(self.training_constants)
        )
        if not referenced <= names:
            raise ValueError("preprocessing references unknown features")
        if set(self.impute_median) & set(self.abstain_if_missing):
            raise ValueError("a feature cannot be both imputed and abstaining")
        values = (*self.impute_median.values(), *self.training_constants.values())
        if not all(math.isfinite(value) for value in values):
            raise ValueError("preprocessing parameters must be finite")
        return self


class ThresholdSpec(_Frozen):
    """Unsupervised review-priority cutoff; never a clinical or hazard threshold."""

    method: Literal["training_score_quantile"]
    quantile: float = Field(gt=0.0, lt=1.0)
    value: float
    selected_on_split: Literal["train"]
    rationale: str = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("threshold must be finite")
        return value


class EstimatorSpec(_Frozen):
    class_name: str = Field(min_length=1)
    params: dict[str, ParamValue]
    runtime_versions: dict[str, str]


class ModelAMetadata(_Frozen):
    metadata_version: Literal["1.0.0"] = MODEL_A_METADATA_VERSION
    model_id: Literal["careyonda-model-a-nasa-rr1-environment-iforest"] = MODEL_A_ID
    model_version: str = Field(min_length=1)
    created_at_utc: datetime
    artifact_file: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset: DatasetProvenance
    features: tuple[FeatureContract, ...] = Field(min_length=1)
    metadata_columns: tuple[str, ...]
    preprocessing: PreprocessingSpec
    estimator: EstimatorSpec
    threshold: ThresholdSpec | None
    training_rows_used: int = Field(ge=1)
    training_rows_excluded: int = Field(ge=0)
    score_definition: str = Field(min_length=1)
    intended_use: str = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)

    @field_validator("created_at_utc")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at_utc must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _feature_alignment(self) -> ModelAMetadata:
        names = tuple(feature.name for feature in self.features)
        if names != self.preprocessing.feature_names:
            raise ValueError("feature contract and preprocessing order differ")
        if set(names) & set(self.metadata_columns):
            raise ValueError("metadata columns must not be predictors")
        return self
