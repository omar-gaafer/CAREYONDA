"""Artificial Model A sidecars; no NASA measurements or fitted artifacts."""

from datetime import timedelta

import pytest

from app.ai.temporal_evidence import analyze_temporal_evidence
from app.application.environmental_anomaly import EnvironmentalAnomalyService
from app.schemas.baseline import ResearchEvidence
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.temporal import TemporalPolicy
from examples.temporal_evidence import synthetic_evidence, synthetic_policy
from tests.environmental_context_fixtures import START, detector, sample


def context_fixture(
    *, unavailable: bool = False
) -> tuple[tuple[ResearchEvidence, ...], TemporalPolicy, EnvironmentalAnomalyContext]:
    samples = tuple(sample(i) for i in (1, 2, 3))
    at = START + timedelta(minutes=15, seconds=1)
    service = EnvironmentalAnomalyService(
        None if unavailable else detector(),
        model_state="unavailable" if unavailable else "available",
    )
    context = service.assess(samples, assessed_at=at)[-1]
    evidence = tuple(
        ResearchEvidence.model_validate(
            {
                "observation": s.observations[0],
                "dataset_id": "artificial",
                "run_id": "test",
                "sensor_id": "artificial-sensor",
                "sensor_epoch": "epoch-1",
                "data_origin": "real",
                "temporal_support": {
                    "start": s.event_time_utc,
                    "end": s.event_time_utc,
                },
            }
        )
        for s in samples
    )
    p = synthetic_policy().model_dump()
    p["scope"] = samples[0].observations[0].scope.model_dump()
    p["source"].update(
        dataset_id="artificial",
        run_id="test",
        source_id="artificial-environment",
        sensor_id="artificial-sensor",
        data_origin="real",
        metric="cabin_co2_concentration",
        unit="ppm",
        maximum_age_seconds=600.0,
    )
    p["event_window"] = {"start": START, "end": samples[-1].event_time_utc}
    p["maximum_gap_seconds"] = 600.0
    p["reference_upper"] = 200.0
    return evidence, TemporalPolicy.model_validate(p), context


@pytest.mark.parametrize("unavailable", [False, True])
def test_context_is_provenance_only(unavailable: bool) -> None:
    e, p, c = context_fixture(unavailable=unavailable)
    before = c.model_dump_json()
    r = analyze_temporal_evidence(
        e, policy=p, assessed_at=c.assessed_at, model_contexts=(c,)
    )
    assert r.pattern == "no_pattern"
    assert r.model_contexts[0].used == (not unavailable)
    assert r.model_contexts[0].context.model == c.model
    assert r.model_contexts[0].context.abstention_reasons == c.abstention_reasons
    assert c.model_dump_json() == before
    if unavailable:
        assert "model_findings_unavailable" in r.missing_or_unavailable


def test_environment_context_cannot_be_attributed_to_astronaut() -> None:
    _, _, c = context_fixture()
    p = synthetic_policy()
    r = analyze_temporal_evidence(
        synthetic_evidence([5.0] * 5),
        policy=p,
        assessed_at=c.assessed_at,
        model_contexts=(c,),
    )
    assert not r.model_contexts[0].used
    assert "model_context_scope_mismatch" in r.model_contexts[0].reason_codes


def test_future_model_assessment_not_used() -> None:
    e, p, c = context_fixture()
    future = EnvironmentalAnomalyContext.model_validate(
        {**c.model_dump(), "assessed_at": c.assessed_at + timedelta(seconds=1)}
    )
    r = analyze_temporal_evidence(
        e, policy=p, assessed_at=c.assessed_at, model_contexts=(future,)
    )
    assert not r.model_contexts[0].used
    assert "model_context_unavailable_at_assessment" in r.model_contexts[0].reason_codes


def test_mismatched_snapshot_not_used() -> None:
    e, p, c = context_fixture()
    changed = e[-1].model_dump()
    changed["observation"]["measurement"]["value"] = 101.0
    e = (*e[:-1], ResearchEvidence.model_validate(changed))
    r = analyze_temporal_evidence(
        e, policy=p, assessed_at=c.assessed_at, model_contexts=(c,)
    )
    assert "model_context_lineage_unavailable" in r.model_contexts[0].reason_codes


@pytest.mark.parametrize("status", ["abstained", "unassessed"])
def test_available_model_without_usable_finding(status: str) -> None:
    e, p, c = context_fixture()
    data = c.model_dump()
    data.update(status=status, threshold=None, threshold_method=None)
    if status == "abstained":
        data.update(
            anomaly_score=None, abstention_reasons=("synthetic_model_abstention",)
        )
    c = EnvironmentalAnomalyContext.model_validate(data)
    r = analyze_temporal_evidence(
        e, policy=p, assessed_at=c.assessed_at, model_contexts=(c,)
    )
    assert r.pattern == "no_pattern"
    assert not r.model_contexts[0].used
    assert "model_finding_unavailable_or_abstained" in r.model_contexts[0].reason_codes
    assert r.model_contexts[0].context.abstention_reasons == c.abstention_reasons


def test_stale_model_context_excluded() -> None:
    e, p, c = context_fixture()
    earlier = sample(1)
    c = EnvironmentalAnomalyContext.model_validate(
        {
            **c.model_dump(),
            "sample": earlier,
            "source_event_time": earlier.event_time_utc,
        }
    )
    r = analyze_temporal_evidence(
        e, policy=p, assessed_at=c.assessed_at, model_contexts=(c,)
    )
    assert r.pattern == "no_pattern"
    assert "model_context_stale" in r.model_contexts[0].reason_codes
