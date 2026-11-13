"""Isolation Forest anomaly detector for synthetic Model B data."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


class IsolationForestAnomalyModel:
    """Train a baseline-only Isolation Forest and score held-out samples."""

    def __init__(
        self,
        feature_names: Sequence[str] | None = None,
        *,
        random_state: int = 42,
        n_estimators: int = 200,
        max_samples: int = 256,
        contamination: float | str = "auto",
    ) -> None:
        self.feature_names = tuple(feature_names or ())
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.training_episode_ids: tuple[str, ...] = ()
        self.pipeline: Pipeline = self._build_pipeline()
        self.feature_means_: NDArray[np.float64] | None = None
        self.feature_stds_: NDArray[np.float64] | None = None

    def _build_pipeline(self) -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    IsolationForest(
                        n_estimators=self.n_estimators,
                        max_samples=self.max_samples,
                        max_features=1.0,
                        bootstrap=False,
                        contamination=self.contamination,
                        n_jobs=1,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )

    def _coerce_matrix(
        self,
        values: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.float64]:
        if isinstance(values, np.ndarray):
            return np.asarray(values, dtype=float)
        rows: list[list[float]] = []
        for row in values:
            if isinstance(row, dict):
                rows.append(
                    [
                        np.nan if row.get(name) in (None, "", "nan", "NaN") else float(row.get(name))
                        for name in self.feature_names
                    ]
                )
            else:
                rows.append(
                    [
                        np.nan if cell in (None, "", "nan", "NaN") else float(cell)
                        for cell in row
                    ]
                )
        return np.asarray(rows, dtype=float)

    def fit(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
        *,
        episode_ids: Sequence[str] | None = None,
    ) -> "IsolationForestAnomalyModel":
        matrix = self._coerce_matrix(X)
        self.pipeline.fit(matrix)
        transformed = self.pipeline.named_steps["imputer"].transform(matrix)
        self.feature_means_ = np.mean(transformed, axis=0)
        self.feature_stds_ = np.std(transformed, axis=0)
        self.feature_stds_ = np.where(self.feature_stds_ == 0.0, 1.0, self.feature_stds_)
        self.training_episode_ids = tuple(episode_ids or ())
        return self

    def _transform(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.float64]:
        matrix = self._coerce_matrix(X)
        return self.pipeline.named_steps["imputer"].transform(matrix)

    def decision_function(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.float64]:
        model = self.pipeline.named_steps["model"]
        return np.asarray(model.decision_function(self._transform(X)), dtype=float)

    def score_samples(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.float64]:
        model = self.pipeline.named_steps["model"]
        return np.asarray(model.score_samples(self._transform(X)), dtype=float)

    def anomaly_score(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.float64]:
        return self.score_samples(X)

    def predict(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
    ) -> NDArray[np.int64]:
        model = self.pipeline.named_steps["model"]
        return np.asarray(model.predict(self._transform(X)), dtype=np.int64)

    def explain(
        self,
        X: Sequence[Sequence[float | int | None | str]] | NDArray[np.float64],
        *,
        top_k: int = 3,
    ) -> list[list[dict[str, Any]]]:
        if self.feature_means_ is None or self.feature_stds_ is None:
            raise ValueError("model is not fitted")
        matrix = self._transform(X)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        explanations: list[list[dict[str, Any]]] = []
        for row in matrix:
            ranked: list[dict[str, Any]] = []
            for idx, name in enumerate(self.feature_names):
                value = float(row[idx])
                baseline_mean = float(self.feature_means_[idx])
                baseline_std = float(self.feature_stds_[idx])
                deviation = (value - baseline_mean) / baseline_std
                ranked.append(
                    {
                        "feature": name,
                        "value": value,
                        "baseline_mean": baseline_mean,
                        "baseline_std": baseline_std,
                        "deviation_z": float(deviation),
                        "direction": (
                            "above_baseline" if value > baseline_mean else "below_baseline"
                        ),
                    }
                )
            ranked.sort(key=lambda item: abs(float(item["deviation_z"])), reverse=True)
            explanations.append(ranked[:top_k])
        return explanations

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            pickle.dump(
                {
                    "feature_names": self.feature_names,
                    "training_episode_ids": self.training_episode_ids,
                    "pipeline": self.pipeline,
                    "feature_means_": self.feature_means_,
                    "feature_stds_": self.feature_stds_,
                    "model_type": "IsolationForest",
                    "model_version": "1.0.0",
                    "random_state": self.random_state,
                    "n_estimators": self.n_estimators,
                    "max_samples": self.max_samples,
                    "contamination": self.contamination,
                },
                handle,
            )
        return target

    @classmethod
    def load(cls, path: str | Path) -> "IsolationForestAnomalyModel":
        target = Path(path)
        with target.open("rb") as handle:
            payload = pickle.load(handle)
        detector = cls(
            feature_names=payload["feature_names"],
            random_state=int(payload["random_state"]),
            n_estimators=int(payload["n_estimators"]),
            max_samples=int(payload["max_samples"]),
            contamination=payload["contamination"],
        )
        detector.pipeline = payload["pipeline"]
        detector.training_episode_ids = tuple(payload.get("training_episode_ids", ()))
        detector.feature_means_ = payload.get("feature_means_")
        detector.feature_stds_ = payload.get("feature_stds_")
        return detector
