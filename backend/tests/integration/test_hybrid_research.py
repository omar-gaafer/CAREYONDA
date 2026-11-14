"""Offline M2/AI-H1/Model A sidecar interactions with entirely synthetic evidence."""

from dataclasses import replace
from datetime import timedelta
from hashlib import sha256

import pytest
from pydantic import ValidationError

from app.ai.research.hybrid import HybridInputError, evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.environmental_anomaly_context import (
    REPLAY_LIMITATIONS,
    EnvironmentalAnomalyContext,
)
from app.schemas.hybrid import HybridAssessment, HybridPolicy
from app.schemas.investigation import Investigation
from examples.hybrid_evidence import synthetic_case
from examples.hybrid_research_cases import (
    ControlledCase,
    artificial_model_context,
    controlled_cases,
)


@pytest.mark.parametrize("case", controlled_cases(), ids=lambda c: c.name)
def test_existing_m2_ranking_is_preserved_with_both_sidecars(
    case: ControlledCase,
) -> None:
    # Exercise real module composition without mocking M2 or AI-H1.
    m2 = case.inputs.investigation
    before = m2.model_dump_json()
    ranks = [(h.hypothesis_id, h.rank, h.compatibility) for h in m2.hypotheses]
    assessment = case.evaluate()
    assert (
        m2.model_dump_json()
        == before
        == assessment.original_investigation.model_dump_json()
    )
    assert [
        (h.hypothesis_id, h.rank, h.compatibility)
        for h in assessment.original_investigation.hypotheses
    ] == ranks
    assert assessment.original_m2_sha256 == sha256(before.encode()).hexdigest()
    assert assessment.original_investigation.safety_status == "not_evaluated"


@pytest.mark.parametrize("flag", ["flagged", "not_flagged", "abstained"])
def test_model_flag_cannot_supply_hazard_direction(flag: str) -> None:
    c = synthetic_case([5.0, 5.0, 20.0, 5.0, 5.0])
    context = artificial_model_context(
        c, flagged=flag == "flagged", not_flagged=flag == "not_flagged"
    )
    without = c.evaluate()
    with_context = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=c.policy,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(context,),
    )
    assert with_context.status == without.status == "insufficient_evidence"
    assert (
        with_context.supporting_evidence_ids
        == without.supporting_evidence_ids
        == ("synthetic-exercise",)
    )
    assert (
        with_context.contradicting_evidence_ids
        == without.contradicting_evidence_ids
        == ()
    )
    trace = with_context.model_reasoning_steps[0]
    assert trace.outcome == "cannot_establish"
    assert not trace.eligible_context
    assert with_context.model_contexts[0] == context
    if flag == "not_flagged":
        assert "not_flagged_does_not_establish_absence" in trace.reason_codes
    elif flag == "flagged":
        assert "statistical_flag_not_hypothesis_evidence" in trace.reason_codes
    else:
        assert "model_finding_unavailable_or_abstained" in trace.reason_codes


def test_replay_is_quarantined_without_losing_original_metadata() -> None:
    case = next(c for c in controlled_cases() if c.name == "F-replay-mismatch")
    r = case.evaluate()
    trace = r.model_reasoning_steps[0]
    assert "historical_replay_not_prospective" in trace.reason_codes
    assert "model_context_scope_mismatch" in trace.reason_codes
    assert not trace.eligible_context
    context = r.model_contexts[0]
    assert context.sample.scope.mission_id == "NASA-RR1"
    assert (
        context.sample.scope.data_origin == "synthetic"
    )  # generated fixture, no NASA data
    assert context.assessment_mode == "historical_replay"
    assert context.evidence_availability_scope == "careyonda_replay"
    assert set(REPLAY_LIMITATIONS) <= set(context.limitations)
    assert all(o.ingested_at is None for o in context.sample.observations)


def test_optional_model_abstention_is_retained_with_valid_measurements() -> None:
    c = synthetic_case()
    ctx = artificial_model_context(c)
    r = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=c.policy,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(ctx,),
    )
    assert r.status == "supported_by_available_evidence"
    assert r.model_contexts[0].abstention_reasons == ("synthetic_model_unavailable",)
    assert not r.model_reasoning_steps[0].eligible_context


def test_future_model_context_not_used() -> None:
    c = synthetic_case()
    ctx = artificial_model_context(c, flagged=True)
    ctx = EnvironmentalAnomalyContext.model_validate(
        {**ctx.model_dump(), "assessed_at": c.assessed_at + timedelta(seconds=1)}
    )
    r = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=c.policy,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(ctx,),
    )
    assert (
        "model_context_unavailable_at_assessment"
        in r.model_reasoning_steps[0].reason_codes
    )
    assert not r.model_reasoning_steps[0].eligible_context


def test_conflicting_model_provenance_never_satisfies_required_context() -> None:
    c = synthetic_case()
    flagged = artificial_model_context(c, flagged=True)
    clear = artificial_model_context(c, not_flagged=True)
    p = HybridPolicy.model_validate(
        {**c.policy.model_dump(), "require_model_context": True}
    )
    r = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=p,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(flagged, clear),
    )
    assert r.status == "insufficient_evidence"
    assert len(r.model_contexts) == 2
    assert all(
        "conflicting_model_context_provenance" in s.reason_codes
        for s in r.model_reasoning_steps
    )
    assert not any(s.eligible_context for s in r.model_reasoning_steps)
    reverse = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=p,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(clear, flagged),
    )
    assert reverse.model_dump_json() == r.model_dump_json()


def test_shared_model_context_is_one_provenance_record_not_two_votes() -> None:
    c = synthetic_case()
    ctx = artificial_model_context(c)
    temporal = analyze_temporal_evidence(
        c.temporal.supporting_evidence,
        policy=c.temporal.policy,
        assessed_at=c.assessed_at,
        model_contexts=(ctx,),
    )
    r = evaluate_hybrid_evidence(
        c.investigation,
        temporal,
        policy=c.policy,
        assessed_at=c.assessed_at,
        m2_evidence=c.evidence,
        model_contexts=(ctx,),
    )
    assert len(r.model_contexts) == len(r.model_reasoning_steps) == 1
    assert r.status == "supported_by_available_evidence"


def test_missing_and_ambiguous_original_hypothesis_rejected() -> None:
    c = synthetic_case()
    for hypotheses in (
        tuple(
            h
            for h in c.investigation.hypotheses
            if h.hypothesis_id != "recent_exercise"
        ),
        (
            *c.investigation.hypotheses,
            next(
                h
                for h in c.investigation.hypotheses
                if h.hypothesis_id == "recent_exercise"
            ),
        ),
    ):
        m2 = Investigation.model_validate(
            {**c.investigation.model_dump(), "hypotheses": hypotheses}
        )
        with pytest.raises(HybridInputError):
            replace(c, investigation=m2).evaluate()


def test_digest_contract_rejects_unrelated_m2_reference() -> None:
    r = synthetic_case().evaluate()
    with pytest.raises(ValidationError, match="digest"):
        HybridAssessment.model_validate(
            {**r.model_dump(), "original_m2_sha256": "0" * 64}
        )


def test_complete_source_and_rule_trace_for_every_directional_relationship() -> None:
    for case in controlled_cases():
        r = case.evaluate()
        snapshots = {e.observation.observation_id: e for e in r.evidence_snapshots}
        rules = {rule.rule_id: rule for rule in r.policy.rules}
        for step in r.reasoning_steps:
            assert step.claim and step.explanation
            if step.outcome in {"supports", "contradicts"}:
                rule = rules[step.rule_id]
                assert rule.rule_version and rule.source_reference
                for oid in (*step.evidence_ids, *step.reference_evidence_ids):
                    e = snapshots[oid]
                    assert e.available_at(r.assessed_at, "prospective")
                    assert e.observation.scope == r.policy.scope
                    assert rule.source.matches(e)
                    assert e.observation.provenance.simulation is not None
                    assert e.observation.quality.status == "valid"
            else:
                assert step.reason_codes
