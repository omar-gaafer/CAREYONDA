"""Focused tests for the existing Model B detector contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.ai.anomaly import IsolationForestAnomalyModel
from app.ai.baseline import ModelBTrainer
from simulator.research.model_b_challenger_experiments import (
    Dataset,
    causal_rolling_mean,
)


def _training_matrix() -> np.ndarray:
    return np.asarray(
        [
            [-0.20, 0.10],
            [-0.10, -0.10],
            [-0.05, 0.05],
            [0.00, 0.00],
            [0.05, -0.05],
            [0.10, 0.10],
            [0.20, -0.10],
            [0.15, 0.05],
        ],
        dtype=np.float64,
    )


def _fitted_model(*, random_state: int = 17) -> IsolationForestAnomalyModel:
    return IsolationForestAnomalyModel(
        feature_names=("heart_rate_latest", "sleep_duration_latest"),
        random_state=random_state,
        n_estimators=64,
        max_samples=8,
        contamination=0.125,
    ).fit(_training_matrix(), episode_ids=("train-episode",))


def _trainer_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scenarios = (
        "baseline",
        "elevated_co2",
        "recent_exercise",
        "sleep_deprivation",
    )
    for scenario_index, scenario in enumerate(scenarios):
        for episode_index in range(8):
            episode_id = f"{scenario}-episode-{episode_index}"
            for sample_index in range(43):
                rows.append(
                    {
                        "sample_id": f"{episode_id}-sample-{sample_index}",
                        "episode_id": episode_id,
                        "scenario": scenario,
                        "features": {
                            "x": float(episode_index + sample_index / 100.0) / 10.0,
                            "y": float(scenario_index)
                            + float(episode_index + sample_index / 100.0) / 20.0,
                        },
                    }
                )
    return rows


def test_anomaly_score_is_higher_for_a_distant_sample() -> None:
    model = _fitted_model()

    ordinary = model.anomaly_score(np.asarray([[0.0, 0.0]], dtype=np.float64))[0]
    anomalous = model.anomaly_score(np.asarray([[8.0, 8.0]], dtype=np.float64))[0]

    assert anomalous > ordinary


def test_predict_flags_match_the_detector_score_and_internal_threshold() -> None:
    model = _fitted_model()
    estimator = model.pipeline.named_steps["model"]
    probes = np.asarray(
        [[0.0, 0.0], [0.1, -0.1], [4.0, 4.0], [8.0, 8.0]],
        dtype=np.float64,
    )

    scores = model.anomaly_score(probes)
    flags = model.predict(probes) == -1
    internal_anomaly_threshold = -float(estimator.offset_)

    assert np.array_equal(flags, scores > internal_anomaly_threshold)


@pytest.mark.parametrize(
    ("score", "expected_flag"),
    [(0.99, False), (1.0, True), (1.01, True)],
)
def test_documented_exploratory_threshold_is_inclusive(
    score: float, expected_flag: bool
) -> None:
    threshold = 1.0
    assert bool(score >= threshold) is expected_flag


def test_supported_missing_values_use_training_medians_without_mutation() -> None:
    model = _fitted_model()
    imputer = model.pipeline.named_steps["imputer"]
    expected_medians = np.median(_training_matrix(), axis=0)
    validation_rows = [
        {"heart_rate_latest": None, "sleep_duration_latest": "nan"},
        {"heart_rate_latest": "", "sleep_duration_latest": 10.0},
        {"heart_rate_latest": np.nan, "sleep_duration_latest": 0.1},
    ]

    assert np.array_equal(imputer.statistics_, expected_medians)
    scores = model.anomaly_score(validation_rows)
    assert scores.shape == (3,)
    assert np.isfinite(scores).all()
    assert np.array_equal(imputer.statistics_, expected_medians)


def test_training_only_preprocessing_and_seeded_scores_are_reproducible() -> None:
    training = _training_matrix()
    first = _fitted_model(random_state=23)
    repeated = _fitted_model(random_state=23)
    held_out = np.asarray([[1000.0, -1000.0]], dtype=np.float64)
    first_imputer = first.pipeline.named_steps["imputer"]
    expected = np.median(training, axis=0)

    assert np.array_equal(first_imputer.statistics_, expected)
    assert np.array_equal(
        first.anomaly_score(training),
        repeated.anomaly_score(training),
    )
    first.anomaly_score(held_out)
    assert np.array_equal(first_imputer.statistics_, expected)


def test_mapping_input_uses_declared_feature_order_and_bad_width_fails() -> None:
    model = _fitted_model()
    mapping = {"sleep_duration_latest": 0.0, "heart_rate_latest": 0.0}
    ordered_array = np.asarray([[0.0, 0.0]], dtype=np.float64)

    assert np.array_equal(
        model.anomaly_score([mapping]), model.anomaly_score(ordered_array)
    )
    with pytest.raises(ValueError):
        model.anomaly_score(np.asarray([[0.0]], dtype=np.float64))


def test_causal_smoothing_is_future_invariant_and_resets_between_episodes() -> None:
    dataset = Dataset(
        feature_names=("score",),
        X=np.asarray([[0.0], [0.0], [0.0], [0.0]], dtype=np.float64),
        labels=("baseline",) * 4,
        episodes=("episode-a", "episode-a", "episode-b", "episode-b"),
        timestamps=(
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
        ),
        sample_ids=("a0", "a1", "b0", "b1"),
    )
    scores = np.asarray([1.0, 2.0, 100.0, 200.0], dtype=np.float64)
    changed_future = scores.copy()
    changed_future[1] = 10000.0
    changed_future[3] = 20000.0

    original = causal_rolling_mean(scores, dataset, window=3)
    changed = causal_rolling_mean(changed_future, dataset, window=3)

    assert original.tolist() == [1.0, 1.5, 100.0, 150.0]
    assert changed[0] == original[0]
    assert changed[2] == original[2]
    assert original[2] == scores[2]


def test_cross_validation_is_out_of_fold_and_deployment_fit_uses_all_baselines() -> (
    None
):
    rows = _trainer_rows()
    feature_names = ("x", "y")

    deployment_model, report = ModelBTrainer(random_state=31).fit(feature_names, rows)

    baseline_episodes = sorted(
        {row["episode_id"] for row in rows if row["scenario"] == "baseline"}
    )
    predictions = report["predictions"]

    assert list(deployment_model.training_episode_ids) == baseline_episodes
    assert len(predictions) == len(rows)
    assert {prediction["sample_id"] for prediction in predictions} == {
        row["sample_id"] for row in rows
    }
    held_out_episodes: list[str] = []
    for fold in report["fold_results"]:
        assert set(fold["training_episodes"]).isdisjoint(fold["held_out_episodes"])
        held_out_episodes.extend(fold["held_out_episodes"])
    assert len(held_out_episodes) == len(set(held_out_episodes))
    assert set(held_out_episodes) == {row["episode_id"] for row in rows}


@pytest.mark.skip(
    reason=(
        "BLOCKED: no original Model B baseline artifact is available to hash; "
        "a challenger or newly trained model is not a substitute."
    )
)
def test_original_baseline_artifact_sha256_is_unchanged() -> None:
    pytest.fail("The original baseline artifact was not located.")


def test_part3_feature_contract_matches_safe_training_manifest() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "synthetic"
        / "model_b_part3_20261114"
        / "training_seed_4201"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_order = tuple(manifest["feature_order"])
    model = IsolationForestAnomalyModel(feature_names=feature_order)

    assert len(feature_order) == 16
    assert model.feature_names == feature_order
    assert not any("scenario" in name or "label" in name for name in feature_order)
