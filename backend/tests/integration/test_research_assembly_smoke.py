"""Assembly acceptance: synthetic fixtures/fake estimators only; no model fitting."""

from datetime import timedelta
from importlib import import_module

import pytest

from app.ai.isolation_confinement import assess_isolation_confinement
from app.ai.research.hybrid import evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.hybrid import HybridPolicy
from examples.hybrid_evidence import synthetic_case
from examples.hybrid_research_cases import controlled_cases
from examples.temporal_evidence import synthetic_evidence, synthetic_policy
from tests.integration.test_temporal_model_context import context_fixture
from tests.unit.test_isolation_confinement import history, numeric, request
from tests.unit.test_model_b_reconciliation import sample, service


def test_all_research_modules_import_without_artifacts() -> None:
    for name in (
        "app.research.model_a_environmental",
        "scripts.analyze_model_a_environmental",
        "app.ai.model_b_anomaly",
        "app.storage.model_b_v1",
        "app.ai.isolation_confinement",
        "app.ai.temporal_evidence",
        "app.ai.research.hybrid",
        "examples.ai_h3_evaluation",
    ):
        assert import_module(name) is not None


def test_environment_finding_stays_outside_astronaut_scope() -> None:
    _, _, context = context_fixture()
    original = context.model_dump_json()
    result = analyze_temporal_evidence(
        synthetic_evidence([5.0] * 5),
        policy=synthetic_policy(),
        assessed_at=context.assessed_at,
        model_contexts=(context,),
    )
    assert not result.model_contexts[0].used
    assert "model_context_scope_mismatch" in result.model_contexts[0].reason_codes
    assert context.model_dump_json() == original


def test_model_b_default_is_scored_but_unassessed() -> None:
    original = sample()
    result = service(original).assess(original)
    assert result.anomaly_score is not None
    assert result.status == "unassessed" and result.flagged is None
    assert result.policy is None
    assert result.sample == original


def test_model_c_preserves_participant_and_rejects_future_support() -> None:
    rows = history()
    valid = request(rows)
    result = assess_isolation_confinement(valid)
    assert (
        result.subject_id == valid.subject_id and result.mission_id == valid.mission_id
    )
    assert result.assessment_interval == valid.assessment_interval
    rows[-1]["temporal_support"]["end"] = valid.assessed_at + timedelta(days=1)
    rejected = numeric(assess_isolation_confinement(request(rows))).findings[-1]
    assert rejected.score_status == "unsupported" and rejected.raw_mad_score is None
    assert "target_support_outside_assessment" in rejected.abstention_reasons


@pytest.mark.parametrize("identity", ["mission_id", "astronaut_id"])
def test_hybrid_rejects_incompatible_context(identity: str) -> None:
    case = synthetic_case()
    scope = {**case.policy.scope.model_dump(), identity: "different-synthetic-context"}
    policy = HybridPolicy.model_validate({**case.policy.model_dump(), "scope": scope})
    result = evaluate_hybrid_evidence(
        case.investigation,
        case.temporal,
        policy=policy,
        assessed_at=case.assessed_at,
        m2_evidence=case.evidence,
    )
    assert result.status == "incompatible_evidence"
    assert not result.supporting_evidence_ids


def test_historical_replay_never_becomes_prospective_astronaut_evidence() -> None:
    case = next(c for c in controlled_cases() if c.name == "F-replay-mismatch")
    result = case.evaluate()
    trace = result.model_reasoning_steps[0]
    assert not trace.eligible_context
    assert "historical_replay_not_prospective" in trace.reason_codes
    assert "model_context_scope_mismatch" in trace.reason_codes
    assert result.model_contexts[0].historical_source_availability == "unknown"
    assert result.model_contexts[0].evidence_availability_scope == "careyonda_replay"


def test_model_research_execution_leaves_m2_outputs_unchanged() -> None:
    case = synthetic_case()
    before = case.investigation.model_dump_json()
    expected = case.evaluate().model_dump_json()
    context_fixture()
    b = sample()
    service(b).assess(b)
    assess_isolation_confinement(request(history()))
    assert case.investigation.model_dump_json() == before
    assert case.evaluate().model_dump_json() == expected
