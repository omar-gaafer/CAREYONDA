"""SYNTHETIC software tests, never clinical validation."""

from datetime import timedelta
from itertools import permutations

import pytest
from pydantic import ValidationError

from app.ai.temporal_evidence import TemporalInputError, analyze_temporal_evidence
from app.schemas.baseline import ResearchEvidence
from app.schemas.temporal import TemporalPolicy, TemporalSummary
from examples.temporal_evidence import START, synthetic_evidence, synthetic_policy


@pytest.mark.parametrize(
    ("values", "pattern"),
    [
        ([20.0, 21.0, 22.0], "persistent_anomaly"),
        ([5.0, 20.0, 5.0], "isolated_spike"),
        ([20.0, 20.0, 5.0, 5.0], "recovery"),
        ([1.0, 3.0, 5.0], "worsening"),
        ([5.0, 3.0, 1.0], "improving"),
        ([5.0, 5.0, 5.0], "no_pattern"),
        ([0.0, 10.0, 0.0], "no_pattern"),
    ],
)
def test_patterns(values: list[float], pattern: str) -> None:
    p = synthetic_policy(len(values))
    r = analyze_temporal_evidence(
        synthetic_evidence(values), policy=p, assessed_at=p.event_window.end
    )
    assert r.pattern == pattern
    assert r.valid_observation_count == len(values)
    assert r.observed_span_seconds == (len(values) - 1) * 60
    assert TemporalSummary.model_validate_json(r.model_dump_json()) == r


def test_direction_is_explicit() -> None:
    p = TemporalPolicy.model_validate(
        {**synthetic_policy(3).model_dump(), "trend_direction": "lower_is_worsening"}
    )
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    assert r.pattern == "improving"
    assert r.slope_per_second == 4.0 / 120


def test_permutations_reproduce_exact_serialization() -> None:
    p = synthetic_policy(3)
    outputs = {
        analyze_temporal_evidence(
            order, policy=p, assessed_at=p.event_window.end
        ).model_dump_json()
        for order in permutations(synthetic_evidence([1.0, 3.0, 5.0]))
    }
    assert len(outputs) == 1


def test_duplicate_identity_rejected() -> None:
    e = synthetic_evidence([1.0, 3.0, 5.0])
    with pytest.raises(TemporalInputError, match="duplicate"):
        analyze_temporal_evidence(
            (*e, e[0]),
            policy=synthetic_policy(3),
            assessed_at=START + timedelta(seconds=180),
        )


@pytest.mark.parametrize("status", ["missing", "unavailable", "invalid", "suspect"])
def test_missing_invalid_break_sequences(status: str) -> None:
    e = list(synthetic_evidence([20.0] * 5))
    data = e[2].model_dump()
    data["observation"]["quality"] = {
        "status": status,
        "reason_codes": ["synthetic_issue"],
    }
    if status in {"missing", "unavailable"}:
        data["observation"]["measurement"] = {
            "kind": "unavailable",
            "reason": "not_received" if status == "missing" else "sensor_offline",
        }
    e[2] = ResearchEvidence.model_validate(data)
    p = synthetic_policy()
    r = analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)
    assert r.pattern == "abstained"
    assert r.valid_observation_count == 4
    assert "incomplete_valid_sequence" in r.abstention_reasons
    assert "quality_" + status in r.missing_or_unavailable
    assert r.excluded_evidence[0].evidence == e[2]


@pytest.mark.parametrize("kind", ["late", "unknown", "future_support"])
def test_unavailable_cannot_influence_pattern(kind: str) -> None:
    p = synthetic_policy(3)
    e = synthetic_evidence([1.0, 3.0, 5.0])
    data = synthetic_evidence([1000.0])[0].model_dump()
    data["observation"]["observation_id"] = "future-hidden"
    if kind == "late":
        data["observation"]["ingested_at"] = p.event_window.end + timedelta(seconds=1)
    elif kind == "unknown":
        data["observation"]["ingested_at"] = None
    else:
        data["temporal_support"]["end"] = p.event_window.end + timedelta(seconds=1)
    future = ResearchEvidence.model_validate(data)
    before = analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)
    after = analyze_temporal_evidence(
        (*e, future), policy=p, assessed_at=p.event_window.end
    )
    assert (after.pattern, after.slope_per_second, after.supporting_evidence) == (
        before.pattern,
        before.slope_per_second,
        before.supporting_evidence,
    )
    assert "unavailable_at_assessment" in after.missing_or_unavailable


@pytest.mark.parametrize(
    "field", ["subject", "mission", "sensor", "epoch", "dataset", "run", "source"]
)
def test_scope_mismatch(field: str) -> None:
    p = synthetic_policy(3)
    e = list(synthetic_evidence([1.0, 3.0, 5.0]))
    data = e[1].model_dump()
    if field in {"subject", "mission"}:
        data["observation"]["scope"][
            "astronaut_id" if field == "subject" else "mission_id"
        ] = "other"
    elif field == "source":
        data["observation"]["provenance"]["source_id"] = "other"
    else:
        data[
            {
                "sensor": "sensor_id",
                "epoch": "sensor_epoch",
                "dataset": "dataset_id",
                "run": "run_id",
            }[field]
        ] = "other"
        if field == "run":
            data["observation"]["provenance"]["simulation"]["run_id"] = "other"
    e[1] = ResearchEvidence.model_validate(data)
    r = analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)
    assert r.pattern == "abstained"
    assert "scope_or_source_mismatch" in r.missing_or_unavailable


@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient(count: int) -> None:
    p = synthetic_policy(3)
    r = analyze_temporal_evidence(
        synthetic_evidence([5.0] * count), policy=p, assessed_at=p.event_window.end
    )
    assert r.pattern == "abstained"
    assert "insufficient_evidence" in r.abstention_reasons
    assert (r.event_span is None) == (count == 0)


def test_stale_and_gap() -> None:
    p = synthetic_policy(10)
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    assert {"stale_observations", "observation_gap"} <= set(r.abstention_reasons)


def test_simultaneous_distinct_ids() -> None:
    e = list(synthetic_evidence([1.0, 3.0, 5.0]))
    data = e[1].model_dump()
    data["observation"]["timestamp"] = e[0].observation.timestamp
    data["temporal_support"] = e[0].temporal_support.model_dump()
    e[1] = ResearchEvidence.model_validate(data)
    p = synthetic_policy(3)
    r = analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)
    assert r.pattern == "abstained"
    assert r.valid_observation_count == 1
    assert "simultaneous_evidence" in r.abstention_reasons


@pytest.mark.parametrize(
    "change",
    [
        {"reference_lower": 20.0, "reference_upper": 10.0},
        {"minimum_slope_per_second": 0.0},
        {"minimum_observations": 2},
        {"minimum_run": 4},
        {"reference_upper": float("inf")},
        {"maximum_gap_seconds": -1.0},
        {"schema_version": "2.0.0"},
    ],
)
def test_invalid_policy(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TemporalPolicy.model_validate({**synthetic_policy().model_dump(), **change})


def test_assessment_boundary() -> None:
    p = synthetic_policy(3)
    e = synthetic_evidence([1.0, 3.0, 5.0])
    with pytest.raises(ValidationError):
        analyze_temporal_evidence(
            e, policy=p, assessed_at=p.event_window.end.replace(tzinfo=None)
        )
    with pytest.raises(TemporalInputError):
        analyze_temporal_evidence(e, policy=p, assessed_at=START)
    assert analyze_temporal_evidence(
        e, policy=p, assessed_at=p.event_window.end
    ).assessed_at.utcoffset() == timedelta(0)


def test_boundary_revalidation_rejects_bypassed_unit() -> None:
    e = list(synthetic_evidence([1.0, 3.0, 5.0]))
    e[0] = e[0].model_copy(
        update={
            "observation": e[0].observation.model_copy(
                update={
                    "measurement": e[0].observation.measurement.model_copy(
                        update={"unit": "Hz"}
                    )
                }
            )
        }
    )
    p = synthetic_policy(3)
    with pytest.raises(ValidationError):
        analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)


def test_window_is_open_left_closed_right_and_support_must_fit() -> None:
    p = synthetic_policy(3)
    e = synthetic_evidence([1.0, 3.0, 5.0])
    data = e[0].model_dump()
    data["observation"]["observation_id"] = "left-boundary"
    data["observation"]["timestamp"] = START
    data["observation"]["ingested_at"] = START
    data["temporal_support"] = {"start": START, "end": START}
    boundary = ResearchEvidence.model_validate(data)
    straddling = e[0].model_dump()
    straddling["observation"]["observation_id"] = "aggregate-straddles"
    straddling["temporal_support"]["start"] = START
    r = analyze_temporal_evidence(
        (*e, boundary, ResearchEvidence.model_validate(straddling)),
        policy=p,
        assessed_at=p.event_window.end,
    )
    assert r.pattern == "worsening"
    assert r.valid_observation_count == 3
    assert len(r.excluded_evidence) == 2
    assert all(x.reason_codes == ("outside_window",) for x in r.excluded_evidence)


def test_freshness_gap_and_slope_equality_are_inclusive() -> None:
    data = synthetic_policy(3).model_dump()
    data["minimum_slope_per_second"] = 4.0 / 120
    data["maximum_gap_seconds"] = 60.0
    data["source"]["maximum_age_seconds"] = 60.0
    p = TemporalPolicy.model_validate(data)
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]),
        policy=p,
        assessed_at=p.event_window.end + timedelta(seconds=60),
    )
    assert r.pattern == "worsening"
    assert not r.abstention_reasons


def test_imperfect_recovery_is_persistent_not_recovered() -> None:
    p = synthetic_policy(3)
    r = analyze_temporal_evidence(
        synthetic_evidence([20.0, 20.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    assert r.pattern == "persistent_anomaly"


def test_source_compatibility_unknown_abstains() -> None:
    data = synthetic_policy(3).model_dump()
    data["source"]["compatibility"] = "unavailable"
    p = TemporalPolicy.model_validate(data)
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    assert "source_compatibility_unavailable" in r.abstention_reasons
    assert not r.supporting_evidence


@pytest.mark.parametrize(
    "change",
    [
        {"valid_observation_count": 99},
        {"observation_ids": ()},
        {"observed_span_seconds": 0.0},
        {"event_span": None},
        {"abstention_reasons": ("invented_reason",)},
    ],
)
def test_summary_rejects_inconsistent_declarations(change: dict[str, object]) -> None:
    p = synthetic_policy(3)
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    with pytest.raises(ValidationError):
        TemporalSummary.model_validate({**r.model_dump(), **change})


def test_inputs_and_provenance_preserved() -> None:
    p = synthetic_policy(3)
    e = synthetic_evidence([1.0, 3.0, 5.0])
    before = [x.model_dump_json() for x in e]
    r = analyze_temporal_evidence(e, policy=p, assessed_at=p.event_window.end)
    assert [x.model_dump_json() for x in e] == before
    assert [x.model_dump_json() for x in r.supporting_evidence] == before
    assert all(
        x.observation.provenance.simulation is not None for x in r.supporting_evidence
    )


def test_offset_times_normalize_to_utc() -> None:
    from datetime import timezone

    p = synthetic_policy(3)
    local = p.event_window.end.astimezone(timezone(timedelta(hours=2)))
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=local
    )
    assert r.assessed_at.isoformat().endswith("+00:00")
    assert r.assessed_at == p.event_window.end


@pytest.mark.parametrize("kind", ["stale", "gap", "count"])
def test_summary_cannot_claim_pattern_without_coverage(kind: str) -> None:
    p = synthetic_policy(3)
    r = analyze_temporal_evidence(
        synthetic_evidence([1.0, 3.0, 5.0]), policy=p, assessed_at=p.event_window.end
    )
    data = r.model_dump()
    if kind == "stale":
        data["assessed_at"] += timedelta(seconds=121)
    elif kind == "gap":
        data["policy"]["maximum_gap_seconds"] = 59.0
    else:
        data["policy"]["minimum_observations"] = 4
    with pytest.raises(ValidationError):
        TemporalSummary.model_validate(data)
