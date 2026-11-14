"""Synthetic bundle tests; joblib deserialization is always replaced by a fake."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]  # pinned package lacks py.typed
import numpy as np
import pytest
from pydantic import ValidationError
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]

from app.features.temporal_features import feature_schema
from app.schemas.model_b import FEATURE_ORDER, FEATURE_UNITS
from app.storage import model_b_v1 as v1
from app.storage.model_b_store import ModelBArtifactError


def bundle(root: Path) -> tuple[str, str]:
    metadata = {
        "schema_version": "1.0.0",
        "model_id": "model-b-synthetic-isolation-forest",
        "model_version": "1.0.0",
        "interpretation": "synthetic_research_only",
        "feature_order": FEATURE_ORDER,
        "feature_units": FEATURE_UNITS,
        "policy": {"baseline_quantile": 0.95},
        "threshold": 0.5,
        "score_definition": "negative_sklearn_score_samples",
        "score_direction": "higher_is_more_anomalous",
        "threshold_comparison": "greater_than",
        "dataset_manifest_sha256": "a" * 64,
        "training_episode_ids": ["synthetic-training-episode"],
        "training_sample_ids": ["synthetic-training-1", "synthetic-training-2"],
        "imputation_medians": [1.0] * 16,
        "descriptive_training_means": [1.0] * 16,
        "descriptive_training_stds": [0.0] * 16,
        "runtime_versions": v1.runtime_versions(),
        "source_code_sha256": {},
        "preprocessing": "median_training_only_no_scaling",
        "effective_max_samples": 2,
    }
    payloads = {
        "metadata.json": json.dumps(metadata).encode(),
        "feature_schema.json": json.dumps(feature_schema(300)).encode(),
        "model_b_pipeline.joblib": b"synthetic-NOT-a-pickle",
        "evaluation.json": b"{}",
        "predictions.csv": b"synthetic-test-only",
    }
    for name, raw in payloads.items():
        (root / name).write_bytes(raw)
    return repin(root), sha256(payloads["model_b_pipeline.joblib"]).hexdigest()


def repin(root: Path) -> str:
    raw = json.dumps(
        {
            "schema_version": "1.0.0",
            "files": {n: sha256((root / n).read_bytes()).hexdigest() for n in v1.FILES},
        }
    ).encode()
    (root / "artifact_manifest.json").write_bytes(raw)
    return sha256(raw).hexdigest()


def fake_pipeline() -> Any:
    # Unfitted sklearn objects with synthetic fitted-state attributes; no fit call.
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    imputer.n_features_in_ = 16
    imputer.statistics_ = np.ones(16)
    estimator = IsolationForest(
        n_estimators=200,
        max_samples=2,
        max_features=1.0,
        bootstrap=False,
        contamination="auto",
        n_jobs=1,
        random_state=42,
    )
    estimator.n_features_in_ = 16
    estimator.estimators_ = [object() for _ in range(200)]
    return Pipeline([("imputer", imputer), ("model", estimator)])


def test_v1_converts_without_approving_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, artifact = bundle(tmp_path)
    monkeypatch.setattr(joblib, "load", lambda _: fake_pipeline())
    loaded = v1.load_trusted_model_b_v1(
        tmp_path,
        trusted_local_artifact=True,
        expected_artifact_sha256=artifact,
        expected_manifest_sha256=manifest,
    )
    assert loaded.model.metadata.schema_version == "2.0.0"
    assert loaded.model.metadata.units == FEATURE_UNITS
    assert loaded.experimental_policy.approval_reference is None
    assert loaded.experimental_policy.decide(0.5) is None
    assert loaded.experimental_policy.comparison == "greater_than"
    assert (
        loaded.original_metadata_sha256
        == sha256((tmp_path / "metadata.json").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize(
    "problem",
    [
        "untrusted",
        "manifest_pin",
        "artifact_pin",
        "corruption",
        "schema",
        "units",
        "runtime",
        "model_version",
        "quantile",
        "linked",
    ],
)
def test_invalid_bundle_never_deserializes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    manifest, artifact = bundle(tmp_path)

    def forbidden(_: object) -> object:
        pytest.fail("invalid artifact reached deserialization")

    monkeypatch.setattr(joblib, "load", forbidden)
    if problem == "manifest_pin":
        manifest = "b" * 64
    elif problem == "artifact_pin":
        artifact = "b" * 64
    elif problem == "corruption":
        (tmp_path / "model_b_pipeline.joblib").write_bytes(b"corrupt")
    elif problem == "schema":
        (tmp_path / "feature_schema.json").write_text("{}")
        manifest = repin(tmp_path)
    elif problem in {"units", "runtime", "model_version", "quantile"}:
        m = json.loads((tmp_path / "metadata.json").read_bytes())
        if problem == "units":
            m["feature_units"][3] = "ppm"
        if problem == "runtime":
            m["runtime_versions"]["scikit-learn"] = "incompatible"
        if problem == "model_version":
            m["model_version"] = "2.0.0"
        if problem == "quantile":
            m["policy"]["baseline_quantile"] = 0.99
        (tmp_path / "metadata.json").write_text(json.dumps(m))
        manifest = repin(tmp_path)
    elif problem == "linked":
        original = tmp_path / "feature_schema.json"
        original.rename(tmp_path / "schema-original.json")
        original.symlink_to(tmp_path / "schema-original.json")
    with pytest.raises((ModelBArtifactError, ValidationError)):
        v1.load_trusted_model_b_v1(
            tmp_path,
            trusted_local_artifact=problem != "untrusted",
            expected_artifact_sha256=artifact,
            expected_manifest_sha256=manifest,
        )


@pytest.mark.parametrize("problem", ["pipeline", "medians", "parameters", "dimensions"])
def test_fitted_state_mismatch_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    manifest, artifact = bundle(tmp_path)
    pipeline = fake_pipeline()
    if problem == "pipeline":
        pipeline = object()
    elif problem == "medians":
        pipeline.named_steps["imputer"].statistics_ = np.zeros(16)
    elif problem == "parameters":
        pipeline.named_steps["model"].random_state = 7
    elif problem == "dimensions":
        pipeline.named_steps["model"].n_features_in_ = 15
    monkeypatch.setattr(joblib, "load", lambda _: pipeline)
    with pytest.raises(ModelBArtifactError):
        v1.load_trusted_model_b_v1(
            tmp_path,
            trusted_local_artifact=True,
            expected_artifact_sha256=artifact,
            expected_manifest_sha256=manifest,
        )
