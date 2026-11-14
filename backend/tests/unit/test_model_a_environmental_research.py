from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from app.research.model_a_environmental import (
    causal_persistence,
    consecutive_flag_episodes,
    recovery_seconds,
    robust_mad_parameters,
    robust_mad_score,
)


def test_raw_mad_baseline_does_not_invent_a_scale_for_flat_data() -> None:
    assert robust_mad_parameters(np.asarray([2.0, 2.0, 2.0])) is None
    fitted = robust_mad_parameters(np.asarray([1.0, 2.0, 3.0, np.nan]))
    assert fitted == (2.0, 1.0)
    assert robust_mad_score(4.0, *fitted) == 2.0
    assert robust_mad_score(4.0, 2.0, 0.0) is None


def test_persistence_is_causal_and_resets_after_long_gap() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=5 * i) for i in range(3)]
    assert causal_persistence(times, [True, False, True]) == [False, False, True]
    times.append(start + timedelta(hours=1))
    assert causal_persistence(times, [True, False, True, True]) == [
        False,
        False,
        True,
        False,
    ]


def test_episodes_and_recovery_only_use_following_scored_readings() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=5 * i) for i in range(7)]
    flags = [False, True, True, False, False, False, True]
    episodes = consecutive_flag_episodes(times, flags)
    assert [episode["row_count"] for episode in episodes] == [2, 1]
    assert recovery_seconds(times, flags, 2) == 15 * 60
    assert (
        recovery_seconds(times, [False, True, True, None, False, False, True], 2)
        is None
    )


def test_persistence_rejects_future_or_duplicate_timestamps() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="strictly increasing"):
        causal_persistence([start, start], [False, False])


def test_persistence_bounds_total_lookback_not_just_adjacent_gaps() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=20 * i) for i in range(3)]
    assert causal_persistence(times, [True, False, True]) == [False, False, False]
    boundary = [start, start + timedelta(minutes=15), start + timedelta(minutes=30)]
    assert causal_persistence(boundary, [True, False, True])[-1] is True
    assert causal_persistence(boundary, [True, False, None])[-1] is None


@pytest.mark.parametrize("missing", [True, False])
def test_recovery_is_censored_before_later_valid_rows(missing: bool) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=5 * i) for i in range(6)]
    flags: list[bool | None] = [True, False, False, False, False, False]
    if missing:
        flags[1] = None
    else:
        times = [times[0], *(t + timedelta(hours=5) for t in times[1:])]
    assert recovery_seconds(times, flags, 0) is None


@pytest.mark.parametrize("seconds,expected", [(1800, True), (1801, False)])
def test_adjacent_gap_boundary_is_explicit(seconds: int, expected: bool) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    assert (
        causal_persistence([start, start + timedelta(seconds=seconds)], [True, True])[
            -1
        ]
        is expected
    )


@pytest.mark.parametrize("seconds", [1800, 1801])
def test_recovery_gap_boundary(seconds: int) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    times = [start + timedelta(seconds=seconds * i) for i in range(4)]
    assert recovery_seconds(times, [True, False, False, False], 0) == (
        3 * seconds if seconds == 1800 else None
    )
