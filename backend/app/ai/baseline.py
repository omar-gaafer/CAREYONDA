"""Train, evaluate, and document the synthetic Model B anomaly detector."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.ai.anomaly import IsolationForestAnomalyModel

SCENARIO_ORDER = (
    "baseline",
    "elevated_co2",
    "recent_exercise",
    "sleep_deprivation",
)


def load_dataset(
    dataset_path: str | Path,
) -> tuple[tuple[str, ...], list[dict[str, Any]]]:
    """Load validated feature rows and labels keyed by sample ID."""
    root = Path(dataset_path)
    with (root / "feature_schema.json").open("r", encoding="utf-8") as handle:
        feature_schema = json.load(handle)
    feature_names = tuple(item["name"] for item in feature_schema["features"])
    with (root / "features.csv").open("r", newline="", encoding="utf-8") as handle:
        feature_rows = list(csv.DictReader(handle))
    with (root / "labels.csv").open("r", newline="", encoding="utf-8") as handle:
        label_rows = list(csv.DictReader(handle))
    label_lookup = {row["sample_id"]: row["synthetic_scenario"] for row in label_rows}
    with (root / "evidence_mapping.json").open("r", encoding="utf-8") as handle:
        evidence_rows = json.load(handle)
    episode_lookup = {
        entry["sample_id"]: entry["context"]["episode_id"] for entry in evidence_rows
    }
    dataset_rows: list[dict[str, Any]] = []
    for row in feature_rows:
        sample_id = row["sample_id"]
        values: dict[str, float | None] = {}
        for name in feature_names:
            raw = row.get(name, "")
            values[name] = None if raw == "" else float(raw)
        dataset_rows.append(
            {
                "sample_id": sample_id,
                "episode_id": episode_lookup[sample_id],
                "scenario": label_lookup[sample_id],
                "features": values,
            }
        )
    return feature_names, dataset_rows


def episode_groups(
    rows: Sequence[dict[str, Any]],
    *,
    scenario_order: Sequence[str] = SCENARIO_ORDER,
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {scenario: [] for scenario in scenario_order}
    for row in rows:
        groups.setdefault(row["scenario"], []).append(row["episode_id"])
    for scenario in groups:
        groups[scenario] = sorted(set(groups[scenario]))
    return groups


def build_grouped_folds(
    rows: Sequence[dict[str, Any]],
    *,
    fold_count: int = 4,
) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    groups = episode_groups(rows)
    folds: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for fold_index in range(fold_count):
        held_out: list[str] = []
        for scenario in SCENARIO_ORDER:
            episodes = groups.get(scenario, [])
            if not episodes:
                continue
            start = fold_index * 2
            stop = start + 2
            held_out.extend(episodes[start:stop])
        held_out = sorted(set(held_out))
        if not held_out:
            continue
        train_baseline = tuple(
            sorted(set(groups.get("baseline", [])) - set(held_out))
        )
        if not train_baseline:
            raise ValueError("every fold needs at least one baseline training episode")
        folds.append((train_baseline, held_out))
    if not folds:
        raise ValueError("no grouped folds available for the supplied dataset")
    return folds


def _feature_matrix(
    rows: Sequence[dict[str, Any]],
    feature_names: Sequence[str],
) -> np.ndarray:
    matrix: list[list[float]] = []
    for row in rows:
        values: list[float] = []
        for name in feature_names:
            raw = row["features"].get(name)
            values.append(np.nan if raw is None else float(raw))
        matrix.append(values)
    return np.asarray(matrix, dtype=float)


def _confusion_counts(y_true: Sequence[int], y_pred: Sequence[int]) -> list[int]:
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return [int(matrix[0, 0]), int(matrix[0, 1]), int(matrix[1, 0]), int(matrix[1, 1])]


def _metric_summary(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_score: Sequence[float],
) -> dict[str, Any]:
    tn, fp, fn, tp = _confusion_counts(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    roc = roc_auc_score(y_true, y_score)
    pr_auc = average_precision_score(y_true, y_score)
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "specificity": float(specificity),
        "roc_auc": float(roc),
        "average_precision": float(pr_auc),
        "confusion_matrix": {
            "labels": ["baseline", "anomaly"],
            "counts": [tn, fp, fn, tp],
        },
        "support": {"baseline": int(tn + fp), "anomaly": int(fn + tp)},
    }


class ModelBTrainer:
    """Train an Isolation Forest on baseline episodes and evaluate with episode splits."""

    def __init__(self, *, random_state: int = 42) -> None:
        self.random_state = random_state

    def fit(
        self,
        feature_names: Sequence[str],
        rows: Sequence[dict[str, Any]],
    ) -> tuple[IsolationForestAnomalyModel, dict[str, Any]]:
        folds = build_grouped_folds(rows)
        detector = IsolationForestAnomalyModel(
            feature_names=feature_names,
            random_state=self.random_state,
        )
        fold_results: list[dict[str, Any]] = []
        all_predictions: list[dict[str, Any]] = []
        for fold_index, (train_eps, test_eps) in enumerate(folds):
            train_rows = [
                row
                for row in rows
                if row["scenario"] == "baseline" and row["episode_id"] in train_eps
            ]
            test_rows = [row for row in rows if row["episode_id"] in test_eps]
            X_train = _feature_matrix(train_rows, feature_names)
            X_test = _feature_matrix(test_rows, feature_names)
            detector.fit(X_train, episode_ids=train_eps)
            y_true = np.array(
                [0 if row["scenario"] == "baseline" else 1 for row in test_rows],
                dtype=int,
            )
            y_pred = (detector.predict(X_test) == -1).astype(int)
            y_score = detector.anomaly_score(X_test)
            summary = _metric_summary(y_true, y_pred, y_score)
            summary["fold"] = fold_index
            summary["training_episodes"] = list(train_eps)
            summary["held_out_episodes"] = list(test_eps)
            fold_results.append(summary)
            for row, score, decision in zip(
                test_rows,
                y_score.tolist(),
                y_pred.tolist(),
                strict=True,
            ):
                all_predictions.append(
                    {
                        "sample_id": row["sample_id"],
                        "episode_id": row["episode_id"],
                        "scenario": row["scenario"],
                        "truth": int(row["scenario"] != "baseline"),
                        "anomaly_score": float(score),
                        "prediction": int(decision),
                    }
                )

        aggregate_metrics = {
            key: float(np.mean([entry[key] for entry in fold_results]))
            for key in (
                "precision",
                "recall",
                "f1",
                "specificity",
                "roc_auc",
                "average_precision",
            )
        }

        scenario_totals: dict[str, Any] = {}
        for scenario_name in ("elevated_co2", "recent_exercise", "sleep_deprivation"):
            scenario_rows = [row for row in rows if row["scenario"] == scenario_name]
            scenario_scores: list[dict[str, Any]] = []
            for _, test_eps in folds:
                current = [
                    row
                    for row in rows
                    if row["episode_id"] in test_eps and row["scenario"] == scenario_name
                ]
                if not current:
                    continue
                X = _feature_matrix(current, feature_names)
                y_true = np.ones(len(current), dtype=int)
                y_pred = (detector.predict(X) == -1).astype(int)
                y_score = detector.anomaly_score(X)
                scenario_scores.append(_metric_summary(y_true, y_pred, y_score))
            if scenario_scores:
                scenario_totals[scenario_name] = {
                    "support": len(scenario_rows),
                    "precision": float(np.mean([item["precision"] for item in scenario_scores])),
                    "recall": float(np.mean([item["recall"] for item in scenario_scores])),
                    "f1": float(np.mean([item["f1"] for item in scenario_scores])),
                    "specificity": float(np.mean([item["specificity"] for item in scenario_scores])),
                    "roc_auc": float(np.mean([item["roc_auc"] for item in scenario_scores])),
                    "average_precision": float(
                        np.mean([item["average_precision"] for item in scenario_scores])
                    ),
                }

        episode_scores: dict[str, list[float]] = defaultdict(list)
        episode_predictions: dict[str, list[int]] = defaultdict(list)
        for prediction in all_predictions:
            episode_scores[prediction["episode_id"]].append(float(prediction["anomaly_score"]))
            episode_predictions[prediction["episode_id"]].append(int(prediction["prediction"]))
        episode_summary = []
        for episode_id in sorted(episode_scores):
            values = episode_scores[episode_id]
            episode_summary.append(
                {
                    "episode_id": episode_id,
                    "median_anomaly_score": float(np.median(values)),
                    "mean_anomaly_score": float(np.mean(values)),
                    "detection_fraction": float(
                        np.mean(episode_predictions[episode_id])
                    ),
                }
            )

        report = {
            "model": {
                "name": "Model B — Multimodal Health Anomaly Detection",
                "type": "IsolationForest",
                "version": "1.0.0",
                "random_state": self.random_state,
                "parameters": {
                    "n_estimators": 200,
                    "max_samples": 256,
                    "max_features": 1.0,
                    "bootstrap": False,
                    "contamination": "auto",
                    "n_jobs": 1,
                },
            },
            "dataset": {
                "feature_order": list(feature_names),
                "scenarios": list(SCENARIO_ORDER),
                "fold_count": len(folds),
            },
            "fold_results": fold_results,
            "aggregate_metrics": aggregate_metrics,
            "scenario_metrics": scenario_totals,
            "episode_metrics": episode_summary,
            "predictions": all_predictions,
        }
        return detector, report


def train_model_b(
    dataset_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train Model B and optionally save the fitted artifact and evaluation report."""
    feature_names, rows = load_dataset(dataset_path)
    trainer = ModelBTrainer(random_state=random_state)
    detector, report = trainer.fit(feature_names, rows)
    if output_dir is not None:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        detector.save(target_dir / "model_b_isolation_forest.pkl")
        (target_dir / "report.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        prediction_rows = [
            {
                "sample_id": row["sample_id"],
                "episode_id": row["episode_id"],
                "scenario": row["scenario"],
                "anomaly_score": row["anomaly_score"],
                "prediction": row["prediction"],
                "truth": row["truth"],
            }
            for row in report["predictions"]
        ]
        with (target_dir / "predictions.csv").open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "sample_id",
                    "episode_id",
                    "scenario",
                    "anomaly_score",
                    "prediction",
                    "truth",
                ],
            )
            writer.writeheader()
            writer.writerows(prediction_rows)
    return report


def load_model_artifact(path: str | Path) -> IsolationForestAnomalyModel:
    """Load a previously serialized detector artifact for offline inference."""
    return IsolationForestAnomalyModel.load(path)
