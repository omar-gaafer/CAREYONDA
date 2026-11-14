"""Research-only Model B challenger experiments on Training and Validation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
from numpy.typing import NDArray
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPOSITORY_ROOT / "datasets" / "synthetic" / "model_b_part3_20261114"
TRAINING_PATH = DATA_ROOT / "training_seed_4201"
VALIDATION_PATH = DATA_ROOT / "validation_seed_4202"
OUTPUT_PATH = DATA_ROOT / "challenger_experiments" / "results.json"
EXPECTED_PROXY = {
    "baseline": 0,
    "benign_exercise_control": 0,
    "elevated_co2": 1,
    "recent_exercise": 1,
    "sleep_deprivation": 1,
}
POSITIVE_SCENARIOS = ("elevated_co2", "recent_exercise", "sleep_deprivation")
SCENARIOS = tuple(EXPECTED_PROXY)
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 4243
ISOLATION_FOREST_SEED = 42
VALIDATION_SPLIT_SEED = 4244
CALIBRATION_FRACTION = 0.5
BASELINE_FPR_TARGETS = (0.01, 0.05, 0.10, 0.20, 0.50)

FloatMatrix = NDArray[np.float64]
IntVector = NDArray[np.int64]
FloatVector = NDArray[np.float64]


@dataclass(frozen=True)
class Dataset:
    feature_names: tuple[str, ...]
    X: FloatMatrix
    labels: tuple[str, ...]
    episodes: tuple[str, ...]
    timestamps: tuple[str, ...]
    sample_ids: tuple[str, ...]
    observation_ids: tuple[str, ...] = ()
    evidence_observation_ids: tuple[str, ...] = ()
    source_payload_sha256: tuple[tuple[str, str], ...] = ()
    source_split: str | None = None
    source_seed: int | None = None
    observation_ids_by_sample: tuple[tuple[str, ...], ...] = ()
    evidence_observation_ids_by_sample: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class Candidate:
    name: str
    kind: str
    feature_indices: tuple[int, ...]
    parameters: dict[str, Any]
    model: Any
    calibration_scores: FloatVector
    scores: FloatVector
    missing_counts: dict[str, int]
    imputation_values: dict[str, float]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested_identifier_values(
    payload: Any,
    identifier_keys: frozenset[str],
    *,
    split: str,
) -> set[str]:
    identifiers: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in identifier_keys:
                identifiers.update(
                    _flatten_identifier_values(value, split=split, key=key)
                )
            else:
                identifiers.update(
                    _nested_identifier_values(value, identifier_keys, split=split)
                )
    elif isinstance(payload, list):
        for value in payload:
            identifiers.update(
                _nested_identifier_values(value, identifier_keys, split=split)
            )
    return identifiers


def _flatten_identifier_values(value: Any, *, split: str, key: str) -> set[str]:
    if isinstance(value, str) and value:
        return {value}
    if isinstance(value, (list, tuple)):
        identifiers: set[str] = set()
        for item in value:
            identifiers.update(_flatten_identifier_values(item, split=split, key=key))
        return identifiers
    if isinstance(value, dict):
        identifiers: set[str] = set()
        for item in value.values():
            identifiers.update(_flatten_identifier_values(item, split=split, key=key))
        return identifiers
    raise ValueError(f"Invalid {key} value in {split} evidence")


def _validate_scenario_proxy(scenario: str, proxy: str, split: str) -> int:
    if scenario not in EXPECTED_PROXY:
        raise ValueError(f"Unknown scenario in {split}")
    expected = str(bool(EXPECTED_PROXY[scenario])).lower()
    if proxy != expected:
        raise ValueError(f"Scenario proxy mapping mismatch in {split}")
    return EXPECTED_PROXY[scenario]


def _assert_disjoint_splits(training: Dataset, validation: Dataset) -> None:
    identifiers = (
        ("episode IDs", set(training.episodes), set(validation.episodes), True),
        ("sample IDs", set(training.sample_ids), set(validation.sample_ids), True),
        (
            "observation IDs",
            set(training.observation_ids),
            set(validation.observation_ids),
            False,
        ),
        (
            "evidence observation IDs",
            set(training.evidence_observation_ids),
            set(validation.evidence_observation_ids),
            False,
        ),
    )
    for label, training_ids, validation_ids, required in identifiers:
        if required and (not training_ids or not validation_ids):
            raise ValueError(f"Cannot verify Training-Validation {label}: IDs missing")
        if not required and bool(training_ids) != bool(validation_ids):
            raise ValueError(
                f"Cannot verify Training-Validation {label}: IDs present in only one split"
            )
        overlap = training_ids & validation_ids
        if overlap:
            raise ValueError(
                f"Training-Validation {label} overlap: {sorted(overlap)[:5]}"
            )


def _subset_dataset(dataset: Dataset, indices: list[int], split_name: str) -> Dataset:
    observation_rows = (
        tuple(dataset.observation_ids_by_sample[index] for index in indices)
        if dataset.observation_ids_by_sample
        else ()
    )
    evidence_rows = (
        tuple(dataset.evidence_observation_ids_by_sample[index] for index in indices)
        if dataset.evidence_observation_ids_by_sample
        else ()
    )
    return Dataset(
        feature_names=dataset.feature_names,
        X=dataset.X[np.asarray(indices, dtype=np.int64)],
        labels=tuple(dataset.labels[index] for index in indices),
        episodes=tuple(dataset.episodes[index] for index in indices),
        timestamps=tuple(dataset.timestamps[index] for index in indices),
        sample_ids=tuple(dataset.sample_ids[index] for index in indices),
        observation_ids=tuple(
            sorted({item for row in observation_rows for item in row})
        ),
        evidence_observation_ids=tuple(
            sorted({item for row in evidence_rows for item in row})
        ),
        source_payload_sha256=dataset.source_payload_sha256,
        source_split=split_name,
        source_seed=dataset.source_seed,
        observation_ids_by_sample=observation_rows,
        evidence_observation_ids_by_sample=evidence_rows,
    )


def split_validation_episodes(
    validation: Dataset,
    *,
    calibration_fraction: float = CALIBRATION_FRACTION,
    seed: int = VALIDATION_SPLIT_SEED,
) -> tuple[Dataset, Dataset]:
    """Split whole episodes deterministically, stratified by scenario."""
    if not 0.0 < calibration_fraction < 1.0:
        raise ValueError("Calibration fraction must be strictly between zero and one")
    if validation.observation_ids_by_sample and len(
        validation.observation_ids_by_sample
    ) != len(validation.sample_ids):
        raise ValueError("Observation ID rows do not match Validation samples")
    if validation.evidence_observation_ids_by_sample and len(
        validation.evidence_observation_ids_by_sample
    ) != len(validation.sample_ids):
        raise ValueError("Evidence observation ID rows do not match Validation samples")
    if validation.observation_ids and not validation.observation_ids_by_sample:
        raise ValueError("Cannot partition Validation observation IDs by episode")
    if (
        validation.evidence_observation_ids
        and not validation.evidence_observation_ids_by_sample
    ):
        raise ValueError(
            "Cannot partition Validation evidence observation IDs by episode"
        )
    if validation.observation_ids_by_sample and set(validation.observation_ids) != {
        item for row in validation.observation_ids_by_sample for item in row
    }:
        raise ValueError("Validation observation ID summary does not match rows")
    if validation.evidence_observation_ids_by_sample and set(
        validation.evidence_observation_ids
    ) != {
        item for row in validation.evidence_observation_ids_by_sample for item in row
    }:
        raise ValueError(
            "Validation evidence observation ID summary does not match rows"
        )

    episode_scenarios: dict[str, set[str]] = defaultdict(set)
    episode_indices: dict[str, list[int]] = defaultdict(list)
    for index, (episode, scenario) in enumerate(
        zip(validation.episodes, validation.labels, strict=True)
    ):
        episode_scenarios[episode].add(scenario)
        episode_indices[episode].append(index)
    if any(len(scenarios) != 1 for scenarios in episode_scenarios.values()):
        raise ValueError("Validation episode has conflicting scenario labels")

    scenario_episodes: dict[str, list[str]] = defaultdict(list)
    for episode, scenarios in episode_scenarios.items():
        scenario_episodes[next(iter(scenarios))].append(episode)
    rng = np.random.default_rng(seed)
    calibration_episodes: set[str] = set()
    for scenario in SCENARIOS:
        episodes = sorted(scenario_episodes.get(scenario, []))
        if len(episodes) < 2:
            raise ValueError(
                f"Need at least two Validation episodes for scenario {scenario}"
            )
        calibration_count = int(len(episodes) * calibration_fraction)
        calibration_count = min(max(calibration_count, 1), len(episodes) - 1)
        calibration_episodes.update(
            str(episodes[index])
            for index in rng.permutation(len(episodes))[:calibration_count]
        )

    calibration_indices: list[int] = []
    evaluation_indices: list[int] = []
    for episode, indices in episode_indices.items():
        target = (
            calibration_indices
            if episode in calibration_episodes
            else evaluation_indices
        )
        target.extend(indices)
    calibration = _subset_dataset(
        validation, calibration_indices, "validation_calibration"
    )
    evaluation = _subset_dataset(
        validation, evaluation_indices, "validation_evaluation"
    )
    _assert_disjoint_splits(calibration, evaluation)
    return calibration, evaluation


def _load_split(path: Path, *, expected_split: str, expected_seed: int) -> Dataset:
    if path.name == "final_test_seed_4203":
        raise ValueError("Final Test is prohibited for challenger experiments")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if manifest["split"] != expected_split or manifest["seed"] != expected_seed:
        raise ValueError(f"Unexpected {expected_split} manifest identity")
    if manifest["sealed"]:
        raise ValueError("A sealed dataset cannot be used for development")

    schema = json.loads((path / "feature_schema.json").read_text(encoding="utf-8"))
    feature_names = tuple(item["name"] for item in schema["features"])
    if feature_names != tuple(manifest["feature_order"]) or len(feature_names) != 16:
        raise ValueError(f"{expected_split} feature schema/order mismatch")
    if manifest["labels_are_features"]:
        raise ValueError(f"{expected_split} labels are marked as features")

    features_file = path / "features.csv"
    labels_file = path / "labels.csv"
    evidence_file = path / "evidence_mapping.json"
    if _sha256(features_file) != manifest["payload_sha256"]["features.csv"]:
        raise ValueError(f"{expected_split} feature file hash mismatch")
    if _sha256(labels_file) != manifest["payload_sha256"]["labels.csv"]:
        raise ValueError(f"{expected_split} label file hash mismatch")
    if _sha256(evidence_file) != manifest["payload_sha256"]["evidence_mapping.json"]:
        raise ValueError(f"{expected_split} evidence file hash mismatch")

    with features_file.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ("sample_id", *feature_names):
            raise ValueError(f"{expected_split} feature CSV header/order mismatch")
        feature_rows = list(reader)
    with labels_file.open("r", newline="", encoding="utf-8") as handle:
        label_reader = csv.DictReader(handle)
        if tuple(label_reader.fieldnames or ()) != (
            "sample_id",
            "synthetic_scenario",
            "expected_anomaly_proxy",
        ):
            raise ValueError(f"{expected_split} label CSV schema mismatch")
        label_rows = list(label_reader)
    evidence_rows = json.loads(evidence_file.read_text(encoding="utf-8"))

    feature_ids = [row["sample_id"] for row in feature_rows]
    label_lookup = {row["sample_id"]: row for row in label_rows}
    evidence_lookup = {row["sample_id"]: row for row in evidence_rows}
    if len(set(feature_ids)) != len(feature_ids):
        raise ValueError(f"{expected_split} duplicate sample IDs")
    if len(label_lookup) != len(label_rows) or len(evidence_lookup) != len(
        evidence_rows
    ):
        raise ValueError(f"{expected_split} duplicate label/evidence sample IDs")
    expected_ids = set(feature_ids)
    if set(label_lookup) != expected_ids or set(evidence_lookup) != expected_ids:
        raise ValueError(f"{expected_split} label/evidence joins are not one-to-one")

    matrix = np.empty((len(feature_rows), len(feature_names)), dtype=np.float64)
    labels: list[str] = []
    episodes: list[str] = []
    timestamps: list[str] = []
    observation_ids_by_sample: list[tuple[str, ...]] = []
    evidence_observation_ids_by_sample: list[tuple[str, ...]] = []
    for row_index, row in enumerate(feature_rows):
        label = label_lookup[row["sample_id"]]
        scenario = label["synthetic_scenario"]
        _validate_scenario_proxy(
            scenario, label["expected_anomaly_proxy"], expected_split
        )
        evidence = evidence_lookup[row["sample_id"]]
        context = evidence["context"]
        labels.append(scenario)
        episodes.append(context["episode_id"])
        timestamps.append(context["timestamp"])
        observation_ids = _nested_identifier_values(
            evidence,
            frozenset(
                {
                    "observation_id",
                    "observation_ids",
                    "source_observation_id",
                    "feature_observation_ids",
                    "window_observation_ids",
                }
            ),
            split=expected_split,
        )
        evidence_observation_ids = _nested_identifier_values(
            evidence,
            frozenset(
                {
                    "evidence_observation_id",
                    "evidence_observation_ids",
                    "feature_observation_ids",
                    "window_observation_ids",
                }
            ),
            split=expected_split,
        )
        observation_ids_by_sample.append(tuple(sorted(observation_ids)))
        evidence_observation_ids_by_sample.append(
            tuple(sorted(evidence_observation_ids))
        )
        for column_index, name in enumerate(feature_names):
            raw = row[name]
            matrix[row_index, column_index] = np.nan if raw == "" else float(raw)
            if not (
                math.isnan(matrix[row_index, column_index])
                or math.isfinite(matrix[row_index, column_index])
            ):
                raise ValueError(f"Non-finite feature in {expected_split}: {name}")

    return Dataset(
        feature_names=feature_names,
        X=matrix,
        labels=tuple(labels),
        episodes=tuple(episodes),
        timestamps=tuple(timestamps),
        sample_ids=tuple(feature_ids),
        observation_ids=tuple(
            sorted({item for row in observation_ids_by_sample for item in row})
        ),
        evidence_observation_ids=tuple(
            sorted({item for row in evidence_observation_ids_by_sample for item in row})
        ),
        source_payload_sha256=tuple(sorted(manifest["payload_sha256"].items())),
        source_split=expected_split,
        source_seed=expected_seed,
        observation_ids_by_sample=tuple(observation_ids_by_sample),
        evidence_observation_ids_by_sample=tuple(evidence_observation_ids_by_sample),
    )


def _feature_groups(names: tuple[str, ...]) -> dict[str, tuple[int, ...]]:
    heart = tuple(i for i, name in enumerate(names) if name.startswith("heart_rate_"))
    exercise = tuple(
        i for i, name in enumerate(names) if name.startswith("exercise_active_")
    )
    if len(heart) != 3 or len(exercise) != 2:
        raise ValueError(
            "Expected feature schema does not contain declared ablation groups"
        )
    return {
        "all_16": tuple(range(len(names))),
        "without_heart_rate": tuple(i for i in range(len(names)) if i not in heart),
        "without_exercise": tuple(i for i in range(len(names)) if i not in exercise),
        "without_heart_rate_or_exercise": tuple(
            i for i in range(len(names)) if i not in set(heart + exercise)
        ),
    }


def _baseline_training_indices(dataset: Dataset) -> IntVector:
    return np.asarray(
        [i for i, scenario in enumerate(dataset.labels) if scenario == "baseline"],
        dtype=np.int64,
    )


def _fit_candidate(
    name: str,
    kind: str,
    train: Dataset,
    calibration: Dataset,
    evaluation: Dataset,
    feature_indices: tuple[int, ...],
    parameters: dict[str, Any],
) -> Candidate:
    train_indices = _baseline_training_indices(train)
    X_train = train.X[np.ix_(train_indices, feature_indices)]
    X_calibration = calibration.X[:, feature_indices]
    X_evaluation = evaluation.X[:, feature_indices]
    feature_names = tuple(train.feature_names[i] for i in feature_indices)
    if np.isnan(X_train).all(axis=0).any():
        raise ValueError(f"{name}: feature entirely missing in training baseline")

    imputer = SimpleImputer(strategy="median")
    imputed_train = np.asarray(imputer.fit_transform(X_train), dtype=np.float64)
    imputed_calibration = np.asarray(imputer.transform(X_calibration), dtype=np.float64)
    imputed_evaluation = np.asarray(imputer.transform(X_evaluation), dtype=np.float64)
    statistics = np.asarray(imputer.statistics_, dtype=np.float64)
    if not np.isfinite(statistics).all():
        raise ValueError(f"{name}: invalid training-only imputation statistics")
    imputation_values = {
        feature_names[i]: float(statistics[i]) for i in range(len(feature_names))
    }

    if kind == "isolation_forest":
        model = IsolationForest(
            n_estimators=int(parameters["n_estimators"]),
            max_samples=parameters["max_samples"],
            max_features=float(parameters["max_features"]),
            bootstrap=False,
            contamination="auto",
            n_jobs=1,
            random_state=int(parameters["random_state"]),
        )
        model.fit(imputed_train)
        calibration_scores = -np.asarray(
            model.score_samples(imputed_calibration), dtype=np.float64
        )
        scores = -np.asarray(model.score_samples(imputed_evaluation), dtype=np.float64)
    elif kind == "robust_mad":
        center = np.median(imputed_train, axis=0)
        scale = 1.4826 * np.median(np.abs(imputed_train - center), axis=0)
        fallback = np.subtract(*np.percentile(imputed_train, [75, 25], axis=0)) / 1.349
        scale = np.where(scale > 0, scale, fallback)
        standard = np.std(imputed_train, axis=0)
        scale = np.where(scale > 0, scale, standard)
        scale = np.where(scale > 0, scale, 1.0)
        calibration_z = (imputed_calibration - center) / scale
        evaluation_z = (imputed_evaluation - center) / scale
        calibration_scores = np.sqrt(np.mean(np.square(calibration_z), axis=1))
        scores = np.sqrt(np.mean(np.square(evaluation_z), axis=1))
        model = {
            "center": center.tolist(),
            "scale": scale.tolist(),
            "scale_rule": "1.4826*MAD; fallback IQR/1.349, then standard deviation, then 1",
        }
    else:
        raise ValueError(f"Unsupported candidate kind: {kind}")

    if (
        calibration_scores.shape != (len(calibration.labels),)
        or scores.shape != (len(evaluation.labels),)
        or not np.isfinite(calibration_scores).all()
        or not np.isfinite(scores).all()
    ):
        raise ValueError(f"{name}: scorer returned invalid values")
    missing_counts = {
        feature_names[i]: int(np.isnan(X_train[:, i]).sum())
        for i in range(len(feature_names))
    }
    return Candidate(
        name=name,
        kind=kind,
        feature_indices=feature_indices,
        parameters=parameters,
        model=model,
        calibration_scores=calibration_scores,
        scores=scores,
        missing_counts=missing_counts,
        imputation_values=imputation_values,
    )


def _ordered_episode_indices(dataset: Dataset) -> list[list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, episode in enumerate(dataset.episodes):
        grouped[episode].append(index)
    return [
        sorted(
            indices,
            key=lambda index: (dataset.timestamps[index], dataset.sample_ids[index]),
        )
        for _, indices in sorted(grouped.items())
    ]


def causal_rolling_mean(
    scores: FloatVector,
    dataset: Dataset,
    *,
    window: int = 3,
) -> FloatVector:
    """Trailing mean using current/past scores only; reset at every episode."""
    if window < 1 or scores.shape != (len(dataset.sample_ids),):
        raise ValueError("Invalid temporal score shape or window")
    result = np.empty_like(scores)
    for indices in _ordered_episode_indices(dataset):
        history: list[float] = []
        for index in indices:
            history.append(float(scores[index]))
            if len(history) > window:
                history.pop(0)
            result[index] = float(np.mean(history))
    return result


def causal_persistence_flags(
    raw_flags: IntVector,
    dataset: Dataset,
    *,
    window: int = 3,
    required: int = 2,
) -> IntVector:
    """Flag when at least `required` of the trailing `window` flags are positive."""
    if window < 1 or not 1 <= required <= window:
        raise ValueError("Invalid persistence rule")
    if raw_flags.shape != (len(dataset.sample_ids),):
        raise ValueError("Invalid persistence flag shape")
    result = np.zeros_like(raw_flags)
    for indices in _ordered_episode_indices(dataset):
        history: list[int] = []
        for index in indices:
            history.append(int(raw_flags[index]))
            if len(history) > window:
                history.pop(0)
            result[index] = int(sum(history) >= required)
    return result


def _average_precision(y_true: IntVector, scores: FloatVector) -> float:
    return float(average_precision_score(y_true, scores))


def _threshold_for_baseline_fpr(
    scores: FloatVector,
    scenarios: tuple[str, ...],
    target: float,
) -> float:
    baseline = scores[np.asarray([s == "baseline" for s in scenarios])]
    if not len(baseline):
        raise ValueError("Validation contains no baseline samples")
    return float(np.quantile(baseline, 1.0 - target, method="higher"))


def _scenario_recall(
    scenarios: tuple[str, ...],
    flags: IntVector,
    scenario: str,
) -> float | None:
    selected = np.asarray([value == scenario for value in scenarios])
    if not selected.any():
        return None
    return float(np.mean(flags[selected]))


def _rate(flags: IntVector, selected: NDArray[np.bool_]) -> float | None:
    return float(np.mean(flags[selected])) if selected.any() else None


def _rate_counts(flags: IntVector, selected: NDArray[np.bool_]) -> dict[str, int]:
    return {
        "numerator": int(flags[selected].sum()),
        "denominator": int(selected.sum()),
    }


def _classification_counts(
    y_true: IntVector, flags: IntVector
) -> dict[str, dict[str, int]]:
    true_positive = int(np.sum((y_true == 1) & (flags == 1)))
    false_positive = int(np.sum((y_true == 0) & (flags == 1)))
    true_negative = int(np.sum((y_true == 0) & (flags == 0)))
    false_negative = int(np.sum((y_true == 1) & (flags == 0)))
    return {
        "true_positive": {"numerator": true_positive, "denominator": len(y_true)},
        "false_positive": {"numerator": false_positive, "denominator": len(y_true)},
        "true_negative": {"numerator": true_negative, "denominator": len(y_true)},
        "false_negative": {"numerator": false_negative, "denominator": len(y_true)},
        "precision": {
            "numerator": true_positive,
            "denominator": true_positive + false_positive,
        },
        "recall": {
            "numerator": true_positive,
            "denominator": true_positive + false_negative,
        },
        "average_precision_positive_samples": {
            "numerator": int(y_true.sum()),
            "denominator": len(y_true),
        },
    }


def _scenario_recall_counts(
    scenarios: tuple[str, ...],
    flags: IntVector,
    scenario: str,
) -> dict[str, int]:
    selected = np.asarray([value == scenario for value in scenarios])
    return {
        "numerator": int(flags[selected].sum()),
        "denominator": int(selected.sum()),
    }


def _episode_metrics(dataset: Dataset, flags: IntVector) -> dict[str, Any]:
    episodes_by_scenario: dict[str, list[tuple[str, list[int]]]] = defaultdict(list)
    indices_by_episode: dict[str, list[int]] = defaultdict(list)
    for index, episode in enumerate(dataset.episodes):
        indices_by_episode[episode].append(index)
    for episode, indices in indices_by_episode.items():
        episode_scenarios = {dataset.labels[index] for index in indices}
        if len(episode_scenarios) != 1:
            raise ValueError(f"Conflicting scenario labels within episode {episode}")
        episodes_by_scenario[episode_scenarios.pop()].append((episode, indices))
    result: dict[str, Any] = {}
    for scenario in SCENARIOS:
        grouped = episodes_by_scenario.get(scenario, [])
        if not grouped:
            continue
        fractions = [
            float(np.mean(flags[np.asarray(indices, dtype=np.int64)]))
            for _, indices in grouped
        ]
        alert_count = int(sum(fraction > 0 for fraction in fractions))
        result[scenario] = {
            "episodes": len(grouped),
            "episodes_with_any_alert": alert_count,
            "episode_alert_rate_numerator": alert_count,
            "episode_alert_rate_denominator": len(grouped),
            "episode_alert_rate": alert_count / len(grouped),
            "mean_within_episode_sample_alert_fraction": float(np.mean(fractions)),
        }
    return result


def _metrics_at_threshold(
    dataset: Dataset,
    scores: FloatVector,
    threshold: float,
) -> dict[str, Any]:
    flags = (scores >= threshold).astype(np.int64)
    y_true = np.asarray(
        [EXPECTED_PROXY[scenario] for scenario in dataset.labels],
        dtype=np.int64,
    )
    baseline = np.asarray([s == "baseline" for s in dataset.labels])
    benign = np.asarray([s == "benign_exercise_control" for s in dataset.labels])
    recent = np.asarray([s == "recent_exercise" for s in dataset.labels])
    exercise_column = dataset.feature_names.index("exercise_active_latest")
    active = np.isfinite(dataset.X[:, exercise_column]) & (
        dataset.X[:, exercise_column] == 1.0
    )
    benign_active = benign & active
    recent_active = recent & active
    counts = _classification_counts(y_true, flags)
    return {
        "threshold": threshold,
        "sample_count": len(dataset.labels),
        "episode_count": len(set(dataset.episodes)),
        "precision": float(precision_score(y_true, flags, zero_division=0)),
        "precision_counts": counts["precision"],
        "recall": float(recall_score(y_true, flags, zero_division=0)),
        "recall_counts": counts["recall"],
        "f1": float(f1_score(y_true, flags, zero_division=0)),
        "pr_auc_average_precision": _average_precision(y_true, scores),
        "pr_auc_positive_sample_counts": counts["average_precision_positive_samples"],
        "positive_prevalence": float(np.mean(y_true)),
        "scenario_recall": {
            scenario: _scenario_recall(dataset.labels, flags, scenario)
            for scenario in POSITIVE_SCENARIOS
        },
        "scenario_recall_counts": {
            scenario: _scenario_recall_counts(dataset.labels, flags, scenario)
            for scenario in POSITIVE_SCENARIOS
        },
        "baseline_false_positive_rate": _rate(flags, baseline),
        "baseline_false_positive_rate_counts": _rate_counts(flags, baseline),
        "benign_exercise_alert_rate_all_samples": _rate(flags, benign),
        "benign_exercise_alert_rate_all_samples_counts": _rate_counts(flags, benign),
        "benign_exercise_alert_rate_active_samples": _rate(flags, benign_active),
        "benign_exercise_alert_rate_active_samples_counts": _rate_counts(
            flags, benign_active
        ),
        "recent_exercise_alert_rate_all_samples": _rate(flags, recent),
        "recent_exercise_alert_rate_all_samples_counts": _rate_counts(flags, recent),
        "recent_exercise_alert_rate_active_samples": _rate(flags, recent_active),
        "recent_exercise_alert_rate_active_samples_counts": _rate_counts(
            flags, recent_active
        ),
        "flagged_samples": int(flags.sum()),
        "episode_metrics": _episode_metrics(dataset, flags),
    }


def _bootstrap_episode_alert_counts(
    sampled_episode_rows: list[tuple[str, list[int]]],
    scores: FloatVector,
    threshold: float,
    scenario: str,
) -> tuple[int, int]:
    episode_draws = [
        row_indices
        for drawn_scenario, row_indices in sampled_episode_rows
        if drawn_scenario == scenario
    ]
    numerator = sum(
        bool(np.any(scores[np.asarray(row_indices, dtype=np.int64)] >= threshold))
        for row_indices in episode_draws
    )
    return numerator, len(episode_draws)


def _bootstrap_operating_point(
    dataset: Dataset,
    scores: FloatVector,
    threshold: float,
    calibration: Dataset,
    calibration_scores: FloatVector,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Stratified episode-cluster bootstrap for rates at a fixed exploratory point."""
    episode_rows: dict[str, list[int]] = defaultdict(list)
    episode_scenario: dict[str, str] = {}
    for index, episode in enumerate(dataset.episodes):
        episode_rows[episode].append(index)
        episode_scenario[episode] = dataset.labels[index]
    episode_groups: dict[str, list[str]] = defaultdict(list)
    for episode, scenario in episode_scenario.items():
        episode_groups[scenario].append(episode)
    for episodes in episode_groups.values():
        episodes.sort()

    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = defaultdict(list)
    calibration_episode_rows: dict[str, list[int]] = defaultdict(list)
    for index, episode in enumerate(calibration.episodes):
        calibration_episode_rows[episode].append(index)
    calibration_baseline_episodes = sorted(
        episode
        for episode, indices in calibration_episode_rows.items()
        if calibration.labels[indices[0]] == "baseline"
    )
    threshold_replicates: list[float] = []
    for _ in range(replicates):
        selected_indices: list[int] = []
        sampled_episode_rows: list[tuple[str, list[int]]] = []
        for scenario in SCENARIOS:
            episodes = episode_groups[scenario]
            sampled = rng.choice(episodes, size=len(episodes), replace=True)
            for episode in sampled:
                current_episode_rows = episode_rows[str(episode)]
                sampled_episode_rows.append((scenario, current_episode_rows))
                selected_indices.extend(current_episode_rows)
        indices = np.asarray(selected_indices, dtype=np.int64)
        sampled_labels = tuple(dataset.labels[i] for i in indices)
        flags = (scores[indices] >= threshold).astype(np.int64)
        baseline = np.asarray([s == "baseline" for s in sampled_labels])
        benign = np.asarray([s == "benign_exercise_control" for s in sampled_labels])
        recent = np.asarray([s == "recent_exercise" for s in sampled_labels])
        exercise_column = dataset.feature_names.index("exercise_active_latest")
        sampled_active = dataset.X[indices, exercise_column]
        active = np.isfinite(sampled_active) & (sampled_active == 1.0)
        y_true = np.asarray(
            [EXPECTED_PROXY[s] for s in sampled_labels],
            dtype=np.int64,
        )
        values["precision"].append(
            float(precision_score(y_true, flags, zero_division=0))
        )
        values["recall"].append(float(recall_score(y_true, flags, zero_division=0)))
        values["f1"].append(float(f1_score(y_true, flags, zero_division=0)))
        values["baseline_false_positive_rate"].append(float(np.mean(flags[baseline])))
        values["benign_exercise_active_alert_rate"].append(
            float(np.mean(flags[benign & active]))
        )
        values["recent_exercise_active_alert_rate"].append(
            float(np.mean(flags[recent & active]))
        )
        for scenario in POSITIVE_SCENARIOS:
            scenario_mask = np.asarray([s == scenario for s in sampled_labels])
            values[f"recall_{scenario}"].append(float(np.mean(flags[scenario_mask])))
        for scenario in SCENARIOS:
            numerator, denominator = _bootstrap_episode_alert_counts(
                sampled_episode_rows,
                scores,
                threshold,
                scenario,
            )
            values[f"episode_alert_rate_{scenario}"].append(numerator / denominator)
        sampled_calibration_episodes = rng.choice(
            calibration_baseline_episodes,
            size=len(calibration_baseline_episodes),
            replace=True,
        )
        calibration_indices = [
            index
            for episode in sampled_calibration_episodes
            for index in calibration_episode_rows[str(episode)]
        ]
        threshold_replicates.append(
            float(
                np.quantile(
                    calibration_scores[calibration_indices],
                    0.95,
                    method="higher",
                )
            )
        )

    return {
        "status": "exploratory",
        "method": "stratified bootstrap resampling whole episodes with replacement within scenario",
        "replicates": replicates,
        "seed": seed,
        "operating_point": "fixed exploratory calibration-baseline empirical 5% quantile; not a selected or approved threshold",
        "conditioning": "Evaluation metric intervals condition on the fitted model, fixed evaluation scores, and fixed calibration-derived threshold; they are not full-pipeline uncertainty estimates.",
        "confidence_interval": "percentile 95%",
        "intervals": {
            name: {
                "lower_2_5_percent": float(np.quantile(observations, 0.025)),
                "median": float(np.quantile(observations, 0.5)),
                "upper_97_5_percent": float(np.quantile(observations, 0.975)),
            }
            for name, observations in sorted(values.items())
        },
        "exploratory_baseline_quantile_threshold_stability": {
            "interpretation": "episode-bootstrap distribution of the empirical 95th percentile of calibration baseline scores; descriptive only",
            "lower_2_5_percent": float(np.quantile(threshold_replicates, 0.025)),
            "median": float(np.quantile(threshold_replicates, 0.5)),
            "upper_97_5_percent": float(np.quantile(threshold_replicates, 0.975)),
        },
    }


def _distribution_summary(dataset: Dataset) -> dict[str, Any]:
    heart_index = dataset.feature_names.index("heart_rate_latest")
    active_index = dataset.feature_names.index("exercise_active_latest")
    result: dict[str, Any] = {}
    for scenario in ("benign_exercise_control", "recent_exercise"):
        mask = np.asarray(
            [
                label == scenario
                and np.isfinite(dataset.X[i, heart_index])
                and dataset.X[i, active_index] == 1.0
                for i, label in enumerate(dataset.labels)
            ]
        )
        values = dataset.X[mask, heart_index]
        result[scenario] = {
            "active_exercise_samples": int(mask.sum()),
            "heart_rate_latest_median": float(np.median(values))
            if len(values)
            else None,
            "heart_rate_latest_mean": float(np.mean(values)) if len(values) else None,
        }
    return result


def run_experiments(
    training: Dataset,
    calibration: Dataset,
    evaluation: Dataset,
    *,
    validation_split_seed: int = VALIDATION_SPLIT_SEED,
    calibration_fraction: float = CALIBRATION_FRACTION,
) -> dict[str, Any]:
    if not (
        training.feature_names == calibration.feature_names == evaluation.feature_names
    ):
        raise ValueError("Training, Calibration, and Evaluation schemas differ")
    _assert_disjoint_splits(training, calibration)
    _assert_disjoint_splits(training, evaluation)
    _assert_disjoint_splits(calibration, evaluation)
    groups = _feature_groups(training.feature_names)
    candidates: list[Candidate] = []
    definitions = (
        (
            "if_reference_200",
            "isolation_forest",
            groups["all_16"],
            {
                "n_estimators": 200,
                "max_samples": 256,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
            },
        ),
        (
            "if_more_trees_500",
            "isolation_forest",
            groups["all_16"],
            {
                "n_estimators": 500,
                "max_samples": 256,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
            },
        ),
        (
            "if_random_subspace_75pct",
            "isolation_forest",
            groups["all_16"],
            {
                "n_estimators": 200,
                "max_samples": 256,
                "max_features": 0.75,
                "random_state": ISOLATION_FOREST_SEED,
            },
        ),
        (
            "if_smaller_subsamples_128",
            "isolation_forest",
            groups["all_16"],
            {
                "n_estimators": 200,
                "max_samples": 128,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
            },
        ),
        (
            "robust_mad_distance",
            "robust_mad",
            groups["all_16"],
            {"scale_rule": "training-baseline median/MAD distance"},
        ),
        (
            "ablation_without_heart_rate",
            "isolation_forest",
            groups["without_heart_rate"],
            {
                "n_estimators": 200,
                "max_samples": 256,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
                "removed_group": "heart_rate_latest,heart_rate_missing,heart_rate_mean",
            },
        ),
        (
            "ablation_without_exercise",
            "isolation_forest",
            groups["without_exercise"],
            {
                "n_estimators": 200,
                "max_samples": 256,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
                "removed_group": "exercise_active_latest,exercise_active_missing",
            },
        ),
        (
            "ablation_without_heart_rate_or_exercise",
            "isolation_forest",
            groups["without_heart_rate_or_exercise"],
            {
                "n_estimators": 200,
                "max_samples": 256,
                "max_features": 1.0,
                "random_state": ISOLATION_FOREST_SEED,
                "removed_groups": ["heart_rate", "exercise"],
            },
        ),
    )
    for name, kind, indices, parameters in definitions:
        candidates.append(
            _fit_candidate(
                name,
                kind,
                training,
                calibration,
                evaluation,
                indices,
                parameters,
            )
        )

    reference = next(
        candidate for candidate in candidates if candidate.name == "if_reference_200"
    )
    smoothed_calibration_scores = causal_rolling_mean(
        reference.calibration_scores, calibration, window=3
    )
    smoothed_scores = causal_rolling_mean(reference.scores, evaluation, window=3)
    smoothed = Candidate(
        name="temporal_causal_3sample_mean",
        kind="causal_trailing_score_mean",
        feature_indices=reference.feature_indices,
        parameters={
            "window_samples": 3,
            "aggregation": "mean(current_and_previous_scores)",
            "reset": "each episode",
        },
        model=None,
        calibration_scores=smoothed_calibration_scores,
        scores=smoothed_scores,
        missing_counts=reference.missing_counts,
        imputation_values=reference.imputation_values,
    )
    candidates.append(smoothed)

    candidate_results: list[dict[str, Any]] = []
    bootstrap_results: dict[str, Any] = {}
    curves: dict[str, Any] = {}
    for candidate in candidates:
        point_threshold = _threshold_for_baseline_fpr(
            candidate.calibration_scores, calibration.labels, 0.05
        )
        point_metrics = _metrics_at_threshold(
            evaluation, candidate.scores, point_threshold
        )
        result = {
            "name": candidate.name,
            "kind": candidate.kind,
            "status": "exploratory",
            "feature_count": len(candidate.feature_indices),
            "parameters": candidate.parameters,
            "evaluation": {
                "average_precision": _average_precision(
                    np.asarray(
                        [EXPECTED_PROXY[s] for s in evaluation.labels], dtype=np.int64
                    ),
                    candidate.scores,
                ),
                "operating_point_5pct_calibration_quantile": point_metrics,
            },
            "training_only_preprocessing": {
                "baseline_training_row_count": len(
                    _baseline_training_indices(training)
                ),
                "feature_order": [
                    training.feature_names[index] for index in candidate.feature_indices
                ],
                "training_baseline_missing_counts": candidate.missing_counts,
                "training_baseline_imputation_values": candidate.imputation_values,
            },
        }
        candidate_results.append(result)
        thresholds: dict[str, Any] = {}
        for target in BASELINE_FPR_TARGETS:
            threshold = _threshold_for_baseline_fpr(
                candidate.calibration_scores, calibration.labels, target
            )
            metrics = _metrics_at_threshold(evaluation, candidate.scores, threshold)
            thresholds[f"calibration_baseline_quantile_{target:.2f}"] = {
                "status": "exploratory",
                "target_calibration_baseline_fpr": target,
                "evaluation_baseline_false_positive_rate": metrics[
                    "baseline_false_positive_rate"
                ],
                "baseline_false_positive_rate_counts": metrics[
                    "baseline_false_positive_rate_counts"
                ],
                "threshold": threshold,
                "precision": metrics["precision"],
                "precision_counts": metrics["precision_counts"],
                "recall": metrics["recall"],
                "recall_counts": metrics["recall_counts"],
                "f1": metrics["f1"],
                "scenario_recall": metrics["scenario_recall"],
                "scenario_recall_counts": metrics["scenario_recall_counts"],
                "benign_exercise_active_alert_rate": metrics[
                    "benign_exercise_alert_rate_active_samples"
                ],
                "benign_exercise_active_alert_rate_counts": metrics[
                    "benign_exercise_alert_rate_active_samples_counts"
                ],
                "recent_exercise_active_alert_rate": metrics[
                    "recent_exercise_alert_rate_active_samples"
                ],
                "recent_exercise_active_alert_rate_counts": metrics[
                    "recent_exercise_alert_rate_active_samples_counts"
                ],
                "baseline_episode_false_alarm_rate": metrics["episode_metrics"][
                    "baseline"
                ]["episode_alert_rate"],
                "baseline_episode_false_alarm_counts": {
                    "numerator": metrics["episode_metrics"]["baseline"][
                        "episode_alert_rate_numerator"
                    ],
                    "denominator": metrics["episode_metrics"]["baseline"][
                        "episode_alert_rate_denominator"
                    ],
                },
                "benign_episode_any_alert_rate": metrics["episode_metrics"][
                    "benign_exercise_control"
                ]["episode_alert_rate"],
                "benign_episode_any_alert_counts": {
                    "numerator": metrics["episode_metrics"]["benign_exercise_control"][
                        "episode_alert_rate_numerator"
                    ],
                    "denominator": metrics["episode_metrics"][
                        "benign_exercise_control"
                    ]["episode_alert_rate_denominator"],
                },
            }
        curves[candidate.name] = thresholds

        bootstrap_results[candidate.name] = _bootstrap_operating_point(
            evaluation,
            candidate.scores,
            point_threshold,
            calibration,
            candidate.calibration_scores,
        )

    reference_baseline_threshold = _threshold_for_baseline_fpr(
        reference.calibration_scores, calibration.labels, 0.05
    )
    reference_raw_flags = (reference.scores >= reference_baseline_threshold).astype(
        np.int64
    )
    persistence_flags = causal_persistence_flags(
        reference_raw_flags, evaluation, window=3, required=2
    )
    persistence_scores = causal_rolling_mean(reference.scores, evaluation, window=3)
    persistence_metrics = {
        "status": "exploratory",
        "decision_rule": "flag when at least 2 of the current/previous two raw reference scores exceed the reference 5% calibration-baseline quantile",
        "raw_reference_threshold": reference_baseline_threshold,
        **_metrics_for_flags(evaluation, persistence_scores, persistence_flags),
    }

    validation_episode_counts = {
        scenario: calibration_count + evaluation_count
        for scenario, calibration_count in __scenario_episode_counts(
            calibration
        ).items()
        for evaluation_count in [__scenario_episode_counts(evaluation).get(scenario, 0)]
    }
    validation_sample_counts = {
        scenario: calibration_count + evaluation_count
        for scenario, calibration_count in __scenario_sample_counts(calibration).items()
        for evaluation_count in [__scenario_sample_counts(evaluation).get(scenario, 0)]
    }

    return {
        "experiment": {
            "status": "exploratory",
            "purpose": "Exploratory research-only challenger comparison; no deployment model or final threshold selected.",
            "training_split": {
                "seed": (
                    training.source_seed if training.source_seed is not None else 4201
                ),
                "episodes": len(set(training.episodes)),
                "samples": len(training.sample_ids),
                "payload_sha256": dict(training.source_payload_sha256),
                "scenario_episode_counts": dict(
                    sorted(__scenario_episode_counts(training).items())
                ),
                "baseline_fit_rows": len(_baseline_training_indices(training)),
            },
            "validation_source": {
                "seed": (
                    calibration.source_seed
                    if calibration.source_seed is not None
                    else 4202
                ),
                "episodes": len(set(calibration.episodes) | set(evaluation.episodes)),
                "samples": len(calibration.sample_ids) + len(evaluation.sample_ids),
                "payload_sha256": dict(calibration.source_payload_sha256),
                "scenario_episode_counts": dict(
                    sorted(validation_episode_counts.items())
                ),
                "scenario_sample_counts": dict(
                    sorted(validation_sample_counts.items())
                ),
            },
            "calibration_subset": {
                **_dataset_counts(calibration),
                "purpose": "exploratory threshold derivation only",
            },
            "evaluation_subset": {
                **_dataset_counts(evaluation),
                "purpose": "candidate performance metrics only",
            },
            "calibration_evaluation_disjointness": {
                "episode_id_overlap_count": len(
                    set(calibration.episodes) & set(evaluation.episodes)
                ),
                "sample_id_overlap_count": len(
                    set(calibration.sample_ids) & set(evaluation.sample_ids)
                ),
                "observation_id_overlap_count": len(
                    set(calibration.observation_ids) & set(evaluation.observation_ids)
                ),
                "evidence_observation_id_overlap_count": len(
                    set(calibration.evidence_observation_ids)
                    & set(evaluation.evidence_observation_ids)
                ),
            },
            "validation_partition": {
                "method": "deterministic scenario-stratified episode split",
                "calibration_fraction": calibration_fraction,
                "seed": validation_split_seed,
                "samples_are_grouped_by_episode": True,
            },
            "feature_order": list(training.feature_names),
            "label_mapping": EXPECTED_PROXY,
            "labels_used_as_features": False,
            "historical_baseline_reproduced": False,
            "b_max": "unapproved; no candidate can be declared budget-compliant",
            "e_max": "unapproved; no candidate can be declared budget-compliant",
            "final_threshold_selected": False,
            "final_test_accessed": False,
            "bootstrap": {
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "stratification": "whole episodes resampled with replacement separately within each scenario",
            },
            "reproducibility": {
                "python_version": platform.python_version(),
                "numpy_version": np.__version__,
                "scikit_learn_version": sklearn.__version__,
                "random_seeds": {
                    "training_split": (
                        training.source_seed
                        if training.source_seed is not None
                        else 4201
                    ),
                    "validation_split": (
                        calibration.source_seed
                        if calibration.source_seed is not None
                        else 4202
                    ),
                    "validation_episode_partition": validation_split_seed,
                    "isolation_forest": ISOLATION_FOREST_SEED,
                    "episode_bootstrap": BOOTSTRAP_SEED,
                },
                "candidate_parameters": {
                    candidate.name: candidate.parameters for candidate in candidates
                },
            },
        },
        "candidate_results": candidate_results,
        "exploratory_baseline_fpr_tradeoffs": curves,
        "temporal_persistence": persistence_metrics,
        "exercise_amplitude_investigation": {
            "training": _distribution_summary(training),
            "evaluation": _distribution_summary(evaluation),
            "note": "Exploratory descriptive active-exercise heart_rate_latest comparison on Evaluation only; scenario metadata is used only for analysis, never as model input.",
        },
        "bootstrap_intervals_at_exploratory_operating_points": bootstrap_results,
        "conclusions": {
            "candidate_advancement": "Exploratory research review only; do not make a final model choice before reviewing validation limits and approving B_max/E_max.",
            "production_readiness": False,
            "threshold_selection": "Not performed.",
        },
    }


def __scenario_episode_counts(dataset: Dataset) -> dict[str, int]:
    by_episode: dict[str, set[str]] = defaultdict(set)
    for episode, scenario in zip(dataset.episodes, dataset.labels, strict=True):
        by_episode[episode].add(scenario)
    if any(len(scenarios) != 1 for scenarios in by_episode.values()):
        raise ValueError("An episode has multiple scenario labels")
    counts: dict[str, int] = defaultdict(int)
    for scenarios in by_episode.values():
        counts[next(iter(scenarios))] += 1
    return dict(counts)


def __scenario_sample_counts(dataset: Dataset) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for scenario in dataset.labels:
        counts[scenario] += 1
    return dict(counts)


def _dataset_counts(dataset: Dataset) -> dict[str, Any]:
    return {
        "episodes": len(set(dataset.episodes)),
        "samples": len(dataset.sample_ids),
        "scenario_episode_counts": dict(
            sorted(__scenario_episode_counts(dataset).items())
        ),
        "scenario_sample_counts": dict(
            sorted(__scenario_sample_counts(dataset).items())
        ),
    }


def _metrics_for_flags(
    dataset: Dataset,
    scores: FloatVector,
    flags: IntVector,
) -> dict[str, Any]:
    y_true = np.asarray([EXPECTED_PROXY[s] for s in dataset.labels], dtype=np.int64)
    baseline = np.asarray([s == "baseline" for s in dataset.labels])
    benign = np.asarray([s == "benign_exercise_control" for s in dataset.labels])
    recent = np.asarray([s == "recent_exercise" for s in dataset.labels])
    exercise_index = dataset.feature_names.index("exercise_active_latest")
    active = np.isfinite(dataset.X[:, exercise_index]) & (
        dataset.X[:, exercise_index] == 1.0
    )
    counts = _classification_counts(y_true, flags)
    return {
        "sample_count": len(dataset.labels),
        "episode_count": len(set(dataset.episodes)),
        "precision": float(precision_score(y_true, flags, zero_division=0)),
        "precision_counts": counts["precision"],
        "recall": float(recall_score(y_true, flags, zero_division=0)),
        "recall_counts": counts["recall"],
        "f1": float(f1_score(y_true, flags, zero_division=0)),
        "pr_auc_average_precision_from_causal_rolling_mean_score": _average_precision(
            y_true, scores
        ),
        "scenario_recall": {
            scenario: _scenario_recall(dataset.labels, flags, scenario)
            for scenario in POSITIVE_SCENARIOS
        },
        "scenario_recall_counts": {
            scenario: _scenario_recall_counts(dataset.labels, flags, scenario)
            for scenario in POSITIVE_SCENARIOS
        },
        "baseline_false_positive_rate": _rate(flags, baseline),
        "baseline_false_positive_rate_counts": _rate_counts(flags, baseline),
        "benign_exercise_alert_rate_all_samples": _rate(flags, benign),
        "benign_exercise_alert_rate_all_samples_counts": _rate_counts(flags, benign),
        "benign_exercise_alert_rate_active_samples": _rate(flags, benign & active),
        "benign_exercise_alert_rate_active_samples_counts": _rate_counts(
            flags, benign & active
        ),
        "recent_exercise_alert_rate_all_samples": _rate(flags, recent),
        "recent_exercise_alert_rate_all_samples_counts": _rate_counts(flags, recent),
        "recent_exercise_alert_rate_active_samples": _rate(flags, recent & active),
        "recent_exercise_alert_rate_active_samples_counts": _rate_counts(
            flags, recent & active
        ),
        "episode_metrics": _episode_metrics(dataset, flags),
    }


def main() -> None:
    training = _load_split(
        TRAINING_PATH,
        expected_split="training",
        expected_seed=4201,
    )
    validation_source = _load_split(
        VALIDATION_PATH,
        expected_split="validation",
        expected_seed=4202,
    )
    calibration, evaluation = split_validation_episodes(validation_source)
    result = run_experiments(
        training,
        calibration,
        evaluation,
        validation_split_seed=VALIDATION_SPLIT_SEED,
        calibration_fraction=CALIBRATION_FRACTION,
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(OUTPUT_PATH)
    print(f"Research results written to {OUTPUT_PATH}")
    print(json.dumps(result["experiment"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
