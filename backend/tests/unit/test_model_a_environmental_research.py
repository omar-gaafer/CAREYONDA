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
