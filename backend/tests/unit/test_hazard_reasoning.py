"""Deterministic synthetic reasoning tests; no clinical validity claims."""

from datetime import UTC, datetime, timedelta

import pytest

from app.ai.hazard_reasoning import ReasoningInputError, investigate
from app.features.temporal_features import SampleAnchor
from app.schemas.investigation import HypothesisId, Investigation
from app.schemas.observation import Observation
from simulator.mission_generator import SimulationConfig, generate_mission


@pytest.fixture
def reference() -> tuple[tuple[Observation, ...], SampleAnchor]:
    mission = generate_mission(
        SimulationConfig(
            steps=3,
            episodes_per_scenario=1,
            noise_scale=0,
            missing_probability=0,
            start=datetime(2026, 11, 12, 23, tzinfo=UTC),
        )
    )
    anchor = next(
        a
        for a in reversed(mission.anchors)
        if mission.labels[a.sample_id] == "baseline"
    )
    return mission.observations, anchor


def case(
    name: HypothesisId = "elevated_co2",
) -> tuple[tuple[Observation, ...], SampleAnchor]:
    mission = generate_mission(
        SimulationConfig(
            steps=3, episodes_per_scenario=1, noise_scale=0, missing_probability=0
        )
    )
    anchor = next(
        a for a in reversed(mission.anchors) if mission.labels[a.sample_id] == name
    )
    return mission.observations, anchor


def replace_metric(
    observations: tuple[Observation, ...],
    anchor: SampleAnchor,
    metric: str,
    measurement: dict[str, object],
) -> tuple[Observation, ...]:
    return tuple(
        Observation.model_validate({**o.model_dump(), "measurement": measurement})
        if o.metric == metric and o.scope.mission_id == anchor.mission_id
        else o
        for o in observations
    )


@pytest.mark.parametrize(
    "name", ["baseline", "elevated_co2", "sleep_deprivation", "recent_exercise"]
)
def test_four_clean_synthetic_patterns(
    reference: tuple[tuple[Observation, ...], SampleAnchor], name: HypothesisId
) -> None:
    observations, anchor = case(name)
    result = investigate(observations, anchor, *reference)
    assert result.selected_hypothesis == name
    assert result.status == "ranked"
    assert result.hypotheses[0].hypothesis_id == name
    assert result.hypotheses[0].compatibility == "supported"
    assert result.hypotheses[0].rank == 1
    assert all(h.uncertainty for h in result.hypotheses)
    assert result.safety_status == "not_evaluated"
    assert Investigation.model_validate_json(result.model_dump_json()) == result
    assert result.timestamp.tzinfo == UTC
    assert len(result.hypotheses) == 4


def test_support_contradiction_and_expected_rules(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case("elevated_co2")
    result = investigate(observations, anchor, *reference)
    co2 = next(h for h in result.hypotheses if h.hypothesis_id == "elevated_co2")
    exercise = next(
        h for h in result.hypotheses if h.hypothesis_id == "recent_exercise"
    )
    assert {e.metric for e in co2.supporting_evidence} == {
        "heart_rate",
        "cabin_co2_partial_pressure",
    }
    assert co2.expected_relations["cabin_co2_partial_pressure"] == "above_reference"
    assert {e.metric for e in exercise.contradictory_evidence} == {"exercise_active"}
    assert exercise.compatibility == "mixed"
    assert all(
        e.observation_ids and e.reference_observation_ids
        for e in co2.supporting_evidence
    )
    assert "causation" in co2.explanation


def test_missing_all_abstains_instead_of_baseline(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    _, anchor = case()
    result = investigate([], anchor, *reference)
    assert result.selected_hypothesis is None
    assert result.status == "insufficient_evidence"
    assert all(h.missing_evidence for h in result.hypotheses)
    assert all(h.rank == 1 for h in result.hypotheses)
    assert all(h.compatibility == "insufficient" for h in result.hypotheses)


def test_missing_reference_does_not_invent_normality() -> None:
    observations, anchor = case()
    reference_anchor = SampleAnchor.model_validate(
        {**anchor.model_dump(), "timestamp": anchor.timestamp - timedelta(hours=1)}
    )
    result = investigate(observations, anchor, [], reference_anchor)
    assert result.selected_hypothesis is None
    assert result.status == "insufficient_evidence"
    assert all(
        e.relation == "missing" for h in result.hypotheses for e in h.missing_evidence
    )


@pytest.mark.parametrize("status", ["suspect", "invalid", "missing", "unavailable"])
def test_quality_limits_traced_and_excluded(
    reference: tuple[tuple[Observation, ...], SampleAnchor], status: str
) -> None:
    observations, anchor = case()
    changed = []
    for o in observations:
        if (
            o.metric != "cabin_co2_partial_pressure"
            or o.scope.mission_id != anchor.mission_id
        ):
            changed.append(o)
            continue
        data = o.model_dump()
        data["quality"] = {"status": status, "reason_codes": ["synthetic_limitation"]}
        if status in {"missing", "unavailable"}:
            data["measurement"] = {
                "kind": "unavailable",
                "reason": "not_received" if status == "missing" else "sensor_offline",
            }
        changed.append(Observation.model_validate(data))
    result = investigate(changed, anchor, *reference)
    co2 = next(h for h in result.hypotheses if h.hypothesis_id == "elevated_co2")
    assert co2.compatibility == "partial"
    assert len(co2.missing_evidence) == 1
    assert len(co2.missing_evidence[0].observation_ids) == 3
    assert len(result.quality_issues) == 3
    assert all(issue.status == status for issue in result.quality_issues)
    assert result.selected_hypothesis is None


def test_partial_dropout_remains_explicit(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    selected = next(
        o
        for o in observations
        if o.metric == "heart_rate" and o.scope.mission_id == anchor.mission_id
    )
    changed = tuple(
        Observation.model_validate(
            {
                **o.model_dump(),
                "measurement": {"kind": "unavailable", "reason": "not_received"},
                "quality": {"status": "missing", "reason_codes": ["synthetic_dropout"]},
            }
        )
        if o.observation_id == selected.observation_id
        else o
        for o in observations
    )
    result = investigate(changed, anchor, *reference)
    assert result.selected_hypothesis == "elevated_co2"
    assert result.quality_issues[0].observation_id == selected.observation_id
    assert any("coverage" in note for note in result.uncertainty)


def test_competing_fully_supported_hypotheses_abstain(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    changed = replace_metric(
        observations, anchor, "exercise_active", {"kind": "boolean", "value": True}
    )
    result = investigate(changed, anchor, *reference)
    assert result.status == "ambiguous"
    assert result.selected_hypothesis is None
    assert {h.hypothesis_id for h in result.hypotheses if h.rank == 1} == {
        "elevated_co2",
        "recent_exercise",
    }


@pytest.mark.parametrize(
    "metric", ["heart_rate", "exercise_active", "fatigue_self_report"]
)
def test_simultaneous_conflict_never_silently_resolves(
    reference: tuple[tuple[Observation, ...], SampleAnchor], metric: str
) -> None:
    observations, anchor = case()
    source = next(
        o
        for o in observations
        if o.metric == metric
        and o.timestamp == anchor.timestamp
        and o.scope.mission_id == anchor.mission_id
    )
    replacement: dict[str, object] = {"kind": "numeric", "value": 999.0, "unit": "bpm"}
    if metric == "exercise_active":
        replacement = {"kind": "boolean", "value": True}
    elif metric == "fatigue_self_report":
        replacement = {
            "kind": "categorical",
            "value": "rested"
            if source.measurement.model_dump()["value"] != "rested"
            else "very_tired",
        }
    duplicate = Observation.model_validate(
        {
            **source.model_dump(),
            "observation_id": "synthetic-conflict",
            "measurement": replacement,
        }
    )
    result = investigate([*observations, duplicate], anchor, *reference)
    assert result.status == "conflicting_evidence"
    assert result.selected_hypothesis is None
    conflict = next(
        e
        for h in result.hypotheses
        for e in h.contradictory_evidence
        if e.relation == "conflicting"
    )
    assert {source.observation_id, duplicate.observation_id} <= set(
        conflict.observation_ids
    )


def test_empirical_bounds_and_exact_equality(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case("baseline")
    result = investigate(observations, anchor, *reference)
    hr = next(
        e for e in result.hypotheses[0].supporting_evidence if e.metric == "heart_rate"
    )
    assert hr.observed_value == hr.reference_minimum == hr.reference_maximum == 72.0
    changed = replace_metric(
        observations,
        anchor,
        "heart_rate",
        {"kind": "numeric", "value": 72.000001, "unit": "bpm"},
    )
    other = investigate(changed, anchor, *reference)
    assert any(
        e.relation == "above_reference"
        for h in other.hypotheses
        for e in h.supporting_evidence
        if e.metric == "heart_rate"
    )


def test_reference_must_be_earlier_and_nonoverlapping(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    with pytest.raises(ReasoningInputError, match="reference must end"):
        investigate(observations, anchor, observations, anchor)
    with pytest.raises(ReasoningInputError, match="window_seconds"):
        investigate(observations, anchor, *reference, window_seconds=0)


def test_reused_id_conflicting_contents_rejected(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    reused = Observation.model_validate(
        {
            **observations[0].model_dump(),
            "metric": "heart_rate",
            "domain": "physiological",
            "scope": {
                "kind": "astronaut",
                "mission_id": anchor.mission_id,
                "astronaut_id": anchor.astronaut_id,
            },
            "measurement": {"kind": "numeric", "value": 123.0, "unit": "bpm"},
        }
    )
    with pytest.raises(ReasoningInputError, match="reuse an observation ID"):
        investigate(observations, anchor, [*reference[0], reused], reference[1])


def test_order_future_and_source_provenance_do_not_control_ranking(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    expected = investigate(observations, anchor, *reference)
    past = tuple(o for o in observations if o.timestamp <= anchor.timestamp)
    source = next(
        o
        for o in observations
        if o.metric == "heart_rate" and o.scope.mission_id == anchor.mission_id
    )
    future = Observation.model_validate(
        {
            **source.model_dump(),
            "observation_id": "future-observation",
            "timestamp": anchor.timestamp + timedelta(seconds=1),
            "ingested_at": anchor.timestamp + timedelta(seconds=2),
            "measurement": {"kind": "numeric", "value": 99999.0, "unit": "bpm"},
        }
    )
    assert expected == investigate(
        [*reversed(past), future], anchor, tuple(reversed(reference[0])), reference[1]
    )
    # Poison every simulator label while preserving observations and identity.
    poisoned = []
    for record in observations:
        data = record.model_dump()
        data["provenance"]["simulation"]["scenario_id"] = "misleading-label"
        poisoned.append(Observation.model_validate(data))
    assert expected == investigate(poisoned, anchor, *reference)


def test_unrelated_mission_or_astronaut_cannot_support(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    altered = SampleAnchor.model_validate(
        {**anchor.model_dump(), "mission_id": "unrelated-mission"}
    )
    assert (
        investigate(observations, altered, *reference).status == "insufficient_evidence"
    )
    altered = SampleAnchor.model_validate(
        {**anchor.model_dump(), "astronaut_id": "other-astronaut"}
    )
    result = investigate(observations, altered, *reference)
    assert result.selected_hypothesis is None
    assert any(
        e.metric == "heart_rate" for h in result.hypotheses for e in h.missing_evidence
    )


def test_bounded_ids_and_reference_identity(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    long_anchor = SampleAnchor.model_validate(
        {**anchor.model_dump(), "sample_id": "a" * 128}
    )
    first = investigate(observations, long_anchor, *reference)
    other = investigate(observations, long_anchor, *reference, window_seconds=120)
    assert len(first.investigation_id) <= 128
    assert first.investigation_id != other.investigation_id


def test_invalid_physical_reading_does_not_create_false_conflict(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    source = next(
        o
        for o in observations
        if o.metric == "heart_rate"
        and o.timestamp == anchor.timestamp
        and o.scope.mission_id == anchor.mission_id
    )
    invalid = Observation.model_validate(
        {
            **source.model_dump(),
            "observation_id": "synthetic-negative-reading",
            "measurement": {"kind": "numeric", "value": -1.0, "unit": "bpm"},
        }
    )
    result = investigate([*observations, invalid], anchor, *reference)
    assert result.selected_hypothesis == "elevated_co2"
    assert result.quality_issues[0].reason_codes == ("physical_domain_violation",)


def test_reference_conflict_abstains(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    source = next(
        o
        for o in reference[0]
        if o.metric == "heart_rate"
        and o.timestamp == reference[1].timestamp
        and o.scope.mission_id == reference[1].mission_id
    )
    conflicting = Observation.model_validate(
        {
            **source.model_dump(),
            "observation_id": "conflicting-reference",
            "measurement": {"kind": "numeric", "value": 99.0, "unit": "bpm"},
        }
    )
    result = investigate(
        observations, anchor, [*reference[0], conflicting], reference[1]
    )
    assert result.selected_hypothesis is None
    assert result.status == "conflicting_evidence"
    assert any(
        "conflicting-reference" in finding.reference_observation_ids
        for h in result.hypotheses
        for finding in h.contradictory_evidence
    )


def test_current_conflict_visible_even_without_numeric_reference(
    reference: tuple[tuple[Observation, ...], SampleAnchor],
) -> None:
    observations, anchor = case()
    source = next(
        o
        for o in observations
        if o.metric == "heart_rate"
        and o.timestamp == anchor.timestamp
        and o.scope.mission_id == anchor.mission_id
    )
    conflicting = Observation.model_validate(
        {
            **source.model_dump(),
            "observation_id": "current-conflict-without-reference",
            "measurement": {"kind": "numeric", "value": 999.0, "unit": "bpm"},
        }
    )
    result = investigate([*observations, conflicting], anchor, [], reference[1])
    assert result.status == "conflicting_evidence"
    assert result.selected_hypothesis is None
    assert any(
        f.relation == "conflicting"
        for h in result.hypotheses
        for f in h.contradictory_evidence
    )
