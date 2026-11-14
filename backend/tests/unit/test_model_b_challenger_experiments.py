"""Tests for research-only Model B challenger utilities."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from simulator.research.model_b_challenger_experiments import (
    Dataset,
    _assert_disjoint_splits,
    _bootstrap_episode_alert_counts,
    _feature_groups,
    _validate_scenario_proxy,
    causal_persistence_flags,
    causal_rolling_mean,
    split_validation_episodes,
)


def _dataset() -> Dataset:
    return Dataset(
        feature_names=("x", "exercise_active_latest"),
        X=np.asarray(
            [
                [0.0, 0.0],
                [1.0, 1.0],
                [2.0, 1.0],
                [3.0, 1.0],
                [4.0, 0.0],
            ],
            dtype=np.float64,
        ),
        labels=("baseline",) * 5,
        episodes=("episode-a", "episode-a", "episode-a", "episode-b", "episode-b"),
        timestamps=(
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            "2026-01-01T00:02:00Z",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
        ),
        sample_ids=("a0", "a1", "a2", "b0", "b1"),
    )


def test_rolling_mean_is_causal_and_resets_at_episode_boundary() -> None:
    dataset = _dataset()
    scores = np.asarray([1.0, 2.0, 6.0, 9.0, 3.0], dtype=np.float64)

    assert causal_rolling_mean(scores, dataset, window=3).tolist() == [
        1.0,
        1.5,
        3.0,
        9.0,
        6.0,
    ]


def test_temporal_helpers_sort_shuffled_samples_within_each_episode() -> None:
    dataset = _dataset()
    scores = np.asarray([1.0, 2.0, 6.0, 9.0, 3.0], dtype=np.float64)
    flags = np.asarray([1, 0, 1, 1, 0], dtype=np.int64)
    permutation = np.asarray([3, 0, 4, 2, 1])
    shuffled = replace(
        dataset,
        X=dataset.X[permutation],
        labels=tuple(dataset.labels[i] for i in permutation),
        episodes=tuple(dataset.episodes[i] for i in permutation),
        timestamps=tuple(dataset.timestamps[i] for i in permutation),
        sample_ids=tuple(dataset.sample_ids[i] for i in permutation),
    )

    ordered_mean = causal_rolling_mean(scores, dataset, window=3)
    shuffled_mean = causal_rolling_mean(scores[permutation], shuffled, window=3)
    ordered_flags = causal_persistence_flags(flags, dataset, window=3, required=2)
    shuffled_flags = causal_persistence_flags(
        flags[permutation], shuffled, window=3, required=2
    )

    assert dict(zip(dataset.sample_ids, ordered_mean, strict=True)) == dict(
        zip(shuffled.sample_ids, shuffled_mean, strict=True)
    )
    assert dict(zip(dataset.sample_ids, ordered_flags, strict=True)) == dict(
        zip(shuffled.sample_ids, shuffled_flags, strict=True)
    )


def test_persistence_requires_two_of_three_and_resets_at_episode_boundary() -> None:
    dataset = _dataset()
    raw_flags = np.asarray([1, 0, 1, 1, 0], dtype=np.int64)

    assert causal_persistence_flags(
        raw_flags, dataset, window=3, required=2
    ).tolist() == [
        0,
        0,
        1,
        0,
        0,
    ]


def test_bootstrap_counts_duplicate_episode_draws_separately() -> None:
    sampled_episode_rows = [
        ("baseline", [0, 1]),
        ("baseline", [0, 1]),
    ]
    scores = np.asarray([0.0, 1.0], dtype=np.float64)

    numerator, denominator = _bootstrap_episode_alert_counts(
        sampled_episode_rows,
        scores,
        threshold=0.5,
        scenario="baseline",
    )

    assert (numerator, denominator) == (2, 2)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("episodes", "episode IDs"),
        ("sample_ids", "sample IDs"),
        ("observation_ids", "observation IDs"),
        ("evidence_observation_ids", "evidence observation IDs"),
    ],
)
def test_training_validation_split_overlap_is_rejected(
    field: str, message: str
) -> None:
    training = replace(
        _dataset(),
        observation_ids=("observation-train",),
        evidence_observation_ids=("evidence-train",),
    )
    validation = replace(
        training,
        episodes=tuple(f"validation-{value}" for value in training.episodes),
        sample_ids=tuple(f"validation-{value}" for value in training.sample_ids),
        observation_ids=("observation-validation",),
        evidence_observation_ids=("evidence-validation",),
    )
    validation = replace(validation, **{field: getattr(training, field)})

    with pytest.raises(ValueError, match=message):
        _assert_disjoint_splits(training, validation)


def test_optional_identifier_overlap_check_fails_closed_when_missing_one_split() -> (
    None
):
    training = replace(_dataset(), observation_ids=("observation-train",))
    validation = replace(
        _dataset(),
        episodes=(
            "validation-a",
            "validation-a",
            "validation-a",
            "validation-b",
            "validation-b",
        ),
        sample_ids=(
            "validation-0",
            "validation-1",
            "validation-2",
            "validation-3",
            "validation-4",
        ),
    )

    with pytest.raises(ValueError, match="present in only one split"):
        _assert_disjoint_splits(training, validation)


def test_scenario_proxy_mapping_is_validated() -> None:
    expected = {
        "baseline": 0,
        "benign_exercise_control": 0,
        "elevated_co2": 1,
        "recent_exercise": 1,
        "sleep_deprivation": 1,
    }
    for scenario, proxy in expected.items():
        assert (
            _validate_scenario_proxy(scenario, str(bool(proxy)).lower(), "validation")
            == proxy
        )

    with pytest.raises(ValueError, match="proxy mapping mismatch"):
        _validate_scenario_proxy("baseline", "true", "training")


def test_validation_episode_split_is_deterministic_stratified_and_disjoint() -> None:
    labels: list[str] = []
    episodes: list[str] = []
    timestamps: list[str] = []
    sample_ids: list[str] = []
    observation_rows: list[tuple[str, ...]] = []
    evidence_rows: list[tuple[str, ...]] = []
    for scenario in (
        "baseline",
        "benign_exercise_control",
        "elevated_co2",
        "recent_exercise",
        "sleep_deprivation",
    ):
        for episode_number in range(2):
            episode = f"{scenario}-episode-{episode_number}"
            for sample_number in range(2):
                sample_id = f"{episode}-sample-{sample_number}"
                labels.append(scenario)
                episodes.append(episode)
                timestamps.append(f"2026-01-01T00:0{sample_number}:00Z")
                sample_ids.append(sample_id)
                observation_rows.append((f"{sample_id}-observation",))
                evidence_rows.append((f"{sample_id}-evidence",))
    validation = Dataset(
        feature_names=("x", "exercise_active_latest"),
        X=np.zeros((len(labels), 2), dtype=np.float64),
        labels=tuple(labels),
        episodes=tuple(episodes),
        timestamps=tuple(timestamps),
        sample_ids=tuple(sample_ids),
        observation_ids=tuple(item[0] for item in observation_rows),
        evidence_observation_ids=tuple(item[0] for item in evidence_rows),
        observation_ids_by_sample=tuple(observation_rows),
        evidence_observation_ids_by_sample=tuple(evidence_rows),
    )

    calibration, evaluation = split_validation_episodes(validation, seed=77)
    repeat_calibration, repeat_evaluation = split_validation_episodes(
        validation, seed=77
    )

    assert calibration.sample_ids == repeat_calibration.sample_ids
    assert evaluation.sample_ids == repeat_evaluation.sample_ids
    assert len(set(calibration.episodes)) == 5
    assert len(set(evaluation.episodes)) == 5
    assert len(calibration.sample_ids) == len(evaluation.sample_ids) == 10
    for subset in (calibration, evaluation):
        assert all(subset.episodes.count(episode) == 2 for episode in subset.episodes)
        assert {
            scenario: sum(label == scenario for label in subset.labels)
            for scenario in set(subset.labels)
        } == {scenario: 2 for scenario in set(subset.labels)}
    assert set(calibration.episodes).isdisjoint(evaluation.episodes)
    assert set(calibration.sample_ids).isdisjoint(evaluation.sample_ids)
    assert set(calibration.sample_ids) | set(evaluation.sample_ids) == set(
        validation.sample_ids
    )
    assert set(calibration.observation_ids).isdisjoint(evaluation.observation_ids)
    assert set(calibration.evidence_observation_ids).isdisjoint(
        evaluation.evidence_observation_ids
    )
    assert set(calibration.labels) == set(evaluation.labels)
    assert all(
        len(
            {
                label
                for label, episode_id in zip(
                    subset.labels, subset.episodes, strict=True
                )
                if episode_id == episode
            }
        )
        == 1
        for subset in (calibration, evaluation)
        for episode in set(subset.episodes)
    )


def test_temporal_helpers_reject_invalid_shapes_and_rules() -> None:
    dataset = _dataset()

    try:
        causal_rolling_mean(np.asarray([1.0]), dataset)
    except ValueError as exc:
        assert "shape" in str(exc)
    else:
        raise AssertionError("Expected invalid score shape to fail")

    try:
        causal_persistence_flags(np.asarray([1, 0, 1, 0, 0]), dataset, required=4)
    except ValueError as exc:
        assert "rule" in str(exc)
    else:
        raise AssertionError("Expected invalid persistence rule to fail")


def test_ablation_groups_match_feature_contract() -> None:
    names = (
        "heart_rate_latest",
        "heart_rate_missing",
        "heart_rate_mean",
        "other",
        "exercise_active_latest",
        "exercise_active_missing",
    )

    groups = _feature_groups(names)

    assert groups["all_16"] == tuple(range(6))
    assert groups["without_heart_rate"] == (3, 4, 5)
    assert groups["without_exercise"] == (0, 1, 2, 3)
    assert groups["without_heart_rate_or_exercise"] == (3,)
