"""Research-only temporal analysis helpers for Model A.

This module does not alter or wrap the production inference contract. Scores are
unsupervised ranking values and never represent probabilities or hazard severity.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

FloatVector = NDArray[np.float64]


def robust_mad_parameters(values: FloatVector) -> tuple[float, float] | None:
    """Return train-only median/raw MAD; zero MAD has no scaled score."""
    observed = values[np.isfinite(values)]
    if observed.size == 0:
        return None
    median = float(np.median(observed))
    mad = float(np.median(np.abs(observed - median)))
    if mad == 0.0:
        return None
    return median, mad


def robust_mad_score(value: float, median: float, mad: float) -> float | None:
    """Absolute deviation/raw MAD, a dimensionless research statistic only."""
    if not math.isfinite(value) or not math.isfinite(median) or mad <= 0:
        return None
    return abs(value - median) / mad


def causal_persistence(
    times: Sequence[datetime],
    flags: Sequence[bool | None],
    *,
    window_rows: int = 3,
    minimum_flags: int = 2,
    reset_gap_seconds: float = 1800.0,
) -> list[bool | None]:
    """At each event, use only current/prior flags within a bounded time window."""
    if len(times) != len(flags):
        raise ValueError("times and flags must have equal lengths")
    if window_rows < 1 or not 1 <= minimum_flags <= window_rows:
        raise ValueError("persistence counts are inconsistent")
    if reset_gap_seconds <= 0 or not math.isfinite(reset_gap_seconds):
        raise ValueError("reset_gap_seconds must be positive")
    output: list[bool | None] = []
    history: list[tuple[datetime, bool | None]] = []
    prior_time: datetime | None = None
    for timestamp, flag in zip(times, flags, strict=True):
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        if prior_time is not None and timestamp <= prior_time:
            raise ValueError("timestamps must be strictly increasing")
        if (
            prior_time is not None
            and (timestamp - prior_time).total_seconds() > reset_gap_seconds
        ):
            history.clear()
        history.append((timestamp, flag))
        history = [
            (time, value)
            for time, value in history[-window_rows:]
            if (timestamp - time).total_seconds() <= reset_gap_seconds
        ]
        assessed = [value for _, value in history if value is not None]
        output.append(None if flag is None else sum(assessed) >= minimum_flags)
        prior_time = timestamp
    return output


def consecutive_flag_episodes(
    times: Sequence[datetime],
    flags: Sequence[bool | None],
    *,
    max_gap_seconds: float = 1800.0,
) -> list[dict[str, object]]:
    """Describe directly consecutive flagged rows, keeping timestamp gaps visible."""
    if len(times) != len(flags):
        raise ValueError("times and flags must have equal lengths")
    episodes: list[dict[str, object]] = []
    active: list[int] = []
    for index, (timestamp, flag) in enumerate(zip(times, flags, strict=True)):
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        connected = bool(
            active
            and 0 < (timestamp - times[active[-1]]).total_seconds() <= max_gap_seconds
        )
        if flag is True and (not active or connected):
            active.append(index)
        else:
            if active:
                episodes.append(_episode(times, active))
                active = []
            if flag is True:
                active = [index]
    if active:
        episodes.append(_episode(times, active))
    return episodes


def _episode(times: Sequence[datetime], indices: list[int]) -> dict[str, object]:
    return {
        "start_utc": times[indices[0]].isoformat(),
        "end_utc": times[indices[-1]].isoformat(),
        "row_count": len(indices),
        "sample_indices": indices,
    }


def recovery_seconds(
    times: Sequence[datetime],
    flags: Sequence[bool | None],
    episode_end_index: int,
    *,
    stable_rows: int = 3,
    reset_gap_seconds: float = 1800.0,
) -> float | None:
    """Time to stable below-threshold readings after an episode, else unknown."""
    if len(times) != len(flags):
        raise ValueError("times and flags must have equal lengths")
    if not 0 <= episode_end_index < len(times) or stable_rows < 1:
        raise ValueError("invalid episode end or stable_rows")
    if reset_gap_seconds <= 0 or not math.isfinite(reset_gap_seconds):
        raise ValueError("reset_gap_seconds must be finite and positive")
    if any(t.tzinfo is None or t.utcoffset() is None for t in times):
        raise ValueError("timestamps must be timezone-aware")
    if any(a >= b for a, b in zip(times, times[1:], strict=False)):
        raise ValueError("timestamps must be strictly increasing")
    count = 0
    for index in range(episode_end_index + 1, len(flags)):
        gap = (times[index] - times[index - 1]).total_seconds()
        if gap <= 0:
            raise ValueError("timestamps must be strictly increasing")
        # Missing follow-up censors this episode; later rows cannot bridge it.
        if gap > reset_gap_seconds or flags[index] is None:
            return None
        if flags[index] is True:
            count = 0
        else:
            count += 1
            if count == stable_rows:
                return (times[index] - times[episode_end_index]).total_seconds()
    return None
