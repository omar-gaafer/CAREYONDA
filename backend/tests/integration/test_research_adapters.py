"""Deterministic synthetic adapter tests; fake model scores, no artifact loading."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.ai.research.evidence_adapters import (
    ResearchAdapterError,
    adapt_environmental,
    adapt_model_b,
    adapt_model_c,
    assess_hybrid,
)
from app.schemas.baseline import ResearchEvidence
from app.schemas.hybrid import HybridPolicy
from app.schemas.isolation_confinement import IsolationConfinementAssessment
from app.schemas.model_b import ModelBFinding
from app.schemas.temporal import TemporalPolicy
from examples.hybrid_evidence import synthetic_case
from examples.hybrid_research_cases import controlled_cases
from examples.research_adapter_demo import build_c_case, demonstration
from tests.integration.test_temporal_model_context import context_fixture
from tests.unit.test_model_b_reconciliation import sample, service


def test_live_environmental_original_source_is_eligible_without_changing_native() -> (
    None
):
    evidence, policy, original = context_fixture()
    before = original.model_dump_json()
    adapted = adapt_environmental(
        original, evidence=evidence, policy=policy, assessed_at=original.assessed_at
    )
    assert adapted.model_context_eligible and adapted.temporal is not None
    assert adapted.native_result.model_dump_json() == before
    assert adapted.temporal.policy.source.unit == "ppm"


@pytest.mark.parametrize("field", ["mission_id", "astronaut_id"])
def test_cross_identity_environment_never_supplies_astronaut_context(
    field: str,
) -> None:
    case = synthetic_case()
    _, _, a = context_fixture()
    scope = {**case.temporal.policy.scope.model_dump(), field: "wrong-identity"}
    policy = TemporalPolicy.model_validate(
        {**case.temporal.policy.model_dump(), "scope": scope}
    )
    adapted = adapt_environmental(
        a, evidence=case.evidence, policy=policy, assessed_at=case.assessed_at
    )
    assert not adapted.model_context_eligible and adapted.temporal is not None
    assert not adapted.temporal.supporting_evidence
    assert adapted.temporal.pattern == "abstained"


@pytest.mark.parametrize(
    "field", ["dataset_id", "run_id", "source_id", "sensor_id", "sensor_epoch"]
)
def test_environmental_source_identity_is_exact(field: str) -> None:
    evidence, policy, a = context_fixture()
    source = {**policy.source.model_dump(), field: "wrong-source"}
    policy = TemporalPolicy.model_validate({**policy.model_dump(), "source": source})
    adapted = adapt_environmental(
        a, evidence=evidence, policy=policy, assessed_at=a.assessed_at
    )
    assert not adapted.model_context_eligible and adapted.temporal is not None
    assert not adapted.temporal.supporting_evidence


def test_no_ppm_to_pa_conversion() -> None:
    _, p, _ = context_fixture()
    with pytest.raises(ValidationError):
        TemporalPolicy.model_validate(
            {**p.model_dump(), "source": {**p.source.model_dump(), "unit": "Pa"}}
        )


@pytest.mark.parametrize("availability", ["missing", "future"])
def test_original_ingestion_is_not_invented(availability: str) -> None:
    evidence, p, a = context_fixture()
    changed = []
    for e in evidence:
        payload = e.model_dump()
        payload["observation"]["ingested_at"] = (
            None if availability == "missing" else a.assessed_at + timedelta(seconds=1)
        )
        changed.append(ResearchEvidence.model_validate(payload))
    result = adapt_environmental(
        a, evidence=changed, policy=p, assessed_at=a.assessed_at
    )
    assert result.temporal is not None and not result.temporal.supporting_evidence
    assert all(
        "unavailable_at_assessment" in x.reason_codes
        for x in result.temporal.excluded_evidence
    )
    assert not result.model_context_eligible


def test_replay_is_preserved_and_never_forwarded_as_prospective() -> None:
    c = next(c for c in controlled_cases() if c.name == "F-replay-mismatch")
    adapted = adapt_environmental(
        c.contexts[0],
        evidence=c.inputs.evidence,
        policy=c.inputs.temporal.policy,
        assessed_at=c.inputs.assessed_at,
    )
    assert adapted.temporal is None and not adapted.model_context_eligible
    assert adapted.native_result == c.contexts[0]
    assert adapted.reason_codes == ("historical_replay_not_prospective",)
    result = assess_hybrid(
        c.inputs.investigation,
        c.inputs.temporal,
        policy=c.inputs.policy,
        assessed_at=c.inputs.assessed_at,
        evidence=c.inputs.evidence,
        contexts=(adapted,),
    )
    assert not result.assessment.model_contexts and result.contexts == (adapted,)


def test_model_b_stays_unassessed_with_full_feature_lineage() -> None:
    s = sample(drop_heart=True)
    original = service(s).assess(s)
    result = adapt_model_b(original, assessed_at=s.assessed_at)
    assert isinstance(result.native_result, ModelBFinding)
    assert (
        result.native_result.status == "unassessed"
        and result.native_result.flagged is None
    )
    assert result.native_result.sample.feature_evidence_ids == s.feature_evidence_ids
    assert result.native_result.imputed_features == original.imputed_features
    assert not result.model_context_eligible and result.temporal is None


def test_model_b_abstention_and_future_context_remain_explicit() -> None:
    s = sample(missing=True)
    original = service(s).assess(s)
    result = adapt_model_b(original, assessed_at=s.assessed_at - timedelta(seconds=1))
    assert "model_b_abstained" in result.reason_codes
    assert "context_unavailable_at_assessment" in result.reason_codes
    assert result.native_result == original


def test_c_sleep_raw_evidence_can_enter_h1_without_converting_scores() -> None:
    req, result, policy = build_c_case()
    adapted = adapt_model_c(req, result, policy=policy, assessed_at=req.assessed_at)
    assert adapted.temporal is not None and adapted.temporal.pattern != "abstained"
    assert adapted.native_result == result and adapted.model_c_request == req
    assert not adapted.model_context_eligible
    assert all(
        e.observation.metric == "sleep_duration"
        for e in adapted.temporal.supporting_evidence
    )
    assert "categorical_fatigue_context_only" in adapted.reason_codes
    assert adapted.temporal.policy.source.unit == "h"


def test_c_does_not_invent_bounds_or_categorical_conversions() -> None:
    req, result, _ = build_c_case()
    adapted = adapt_model_c(req, result, policy=None, assessed_at=req.assessed_at)
    assert adapted.temporal is None and adapted.native_result == result
    assert "explicit_sleep_temporal_policy_required" in adapted.reason_codes
    assert "categorical_fatigue_context_only" in adapted.reason_codes


@pytest.mark.parametrize("field", ["subject_id", "mission_id", "dataset_id", "run_id"])
def test_c_request_result_pairing_rejects_wrong_identity(field: str) -> None:
    req, result, policy = build_c_case()
    mismatched = IsolationConfinementAssessment.model_validate(
        {**result.model_dump(), field: "different"}
    )
    with pytest.raises(ResearchAdapterError):
        adapt_model_c(req, mismatched, policy=policy, assessed_at=req.assessed_at)


def test_c_rejects_future_result_and_incompatible_policy_window() -> None:
    req, result, policy = build_c_case()
    adapted = adapt_model_c(
        req, result, policy=policy, assessed_at=req.assessed_at - timedelta(seconds=1)
    )
    assert (
        adapted.temporal is None
        and "context_unavailable_at_assessment" in adapted.reason_codes
    )
    wrong = TemporalPolicy.model_validate(
        {
            **policy.model_dump(),
            "scope": {**policy.scope.model_dump(), "astronaut_id": "wrong"},
        }
    )
    assert (
        adapt_model_c(req, result, policy=wrong, assessed_at=req.assessed_at).temporal
        is None
    )


def test_hybrid_compatible_case_keeps_m2_and_contexts_independent() -> None:
    case = synthetic_case()
    before = case.investigation.model_dump_json()
    s = sample()
    b = adapt_model_b(service(s).assess(s), assessed_at=s.assessed_at)
    result = assess_hybrid(
        case.investigation,
        case.temporal,
        policy=case.policy,
        assessed_at=case.assessed_at,
        evidence=case.evidence,
        contexts=(b,),
    )
    assert result.assessment.status == "supported_by_available_evidence"
    assert result.assessment.original_investigation.model_dump_json() == before
    assert case.investigation.model_dump_json() == before
    assert result.contexts == (b,) and not result.assessment.model_contexts


@pytest.mark.parametrize("field", ["mission_id", "astronaut_id"])
def test_hybrid_wrong_scope_rejected(field: str) -> None:
    case = synthetic_case()
    policy = HybridPolicy.model_validate(
        {
            **case.policy.model_dump(),
            "scope": {**case.policy.scope.model_dump(), field: "wrong"},
        }
    )
    r = assess_hybrid(
        case.investigation,
        case.temporal,
        policy=policy,
        assessed_at=case.assessed_at,
        evidence=case.evidence,
    )
    assert (
        r.assessment.status == "incompatible_evidence"
        and not r.assessment.supporting_evidence_ids
    )


def test_demo_is_deterministic_and_rejects_future_support() -> None:
    result = demonstration()
    assert result == demonstration()
    assert result["model_b_status"] == "unassessed"
    assert result["historical_replay_eligible"] is False
    assert result["cross_subject_usable_observations"] == 0
    assert result["future_support_excluded"] is True
    assert result["m2_unchanged"] is True


def test_c_reference_observations_must_match_native_baseline() -> None:
    req, result, policy = build_c_case()
    rows = list(req.evidence)
    target = next(
        i for i, e in enumerate(rows) if e.observation.observation_id == "syn-sleep-00"
    )
    payload = rows[target].model_dump()
    payload["observation"]["measurement"]["value"] += 0.1
    rows[target] = ResearchEvidence.model_validate(payload)
    changed = req.model_validate({**req.model_dump(), "evidence": tuple(rows)})
    with pytest.raises(ResearchAdapterError, match="reference lineage"):
        adapt_model_c(changed, result, policy=policy, assessed_at=req.assessed_at)
