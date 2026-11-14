"""Repository-local SYNTHETIC research demonstration; no telemetry or trained models.

Uses existing deterministic synthetic fixture factories, explicitly including fake
Model B estimator scores. Fixture ingestion times are simulation declarations,
not authoritative NASA or real astronaut acquisition records.
"""

from __future__ import annotations

import json
from datetime import timedelta

from app.ai.isolation_confinement import assess_isolation_confinement
from app.ai.research.evidence_adapters import (
    adapt_environmental,
    adapt_model_b,
    adapt_model_c,
    assess_hybrid,
)
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.isolation_confinement import (
    IsolationConfinementAssessment,
    ModelCRequest,
)
from app.schemas.temporal import TemporalPolicy
from examples.hybrid_evidence import synthetic_case
from examples.hybrid_research_cases import controlled_cases
from examples.temporal_evidence import synthetic_policy
from tests.integration.test_temporal_model_context import context_fixture
from tests.unit.test_isolation_confinement import (
    REFERENCE_DAYS,
    fatigue,
    history,
    request,
)
from tests.unit.test_model_b_reconciliation import sample, service


def build_c_case() -> tuple[
    ModelCRequest, IsolationConfinementAssessment, TemporalPolicy
]:
    """Synthetic C request/result and explicitly arbitrary software-test policy."""
    req = request(
        history() + [fatigue("synthetic-fatigue-context", "tired", REFERENCE_DAYS)],
        indicators=("sleep_duration", "fatigue_self_report"),
    )
    result = assess_isolation_confinement(req)
    data = synthetic_policy().model_dump()
    data.update(
        scope={
            "kind": "astronaut",
            "astronaut_id": req.subject_id,
            "mission_id": req.mission_id,
        },
        event_window=req.assessment_interval.model_dump(),
        reference_lower=6.0,
        reference_upper=9.0,
        maximum_gap_seconds=200000.0,
        minimum_observations=3,
        convention_reference="SYNTHETIC adapter software-test bounds; no clinical validity",
    )
    source = next(s for s in req.sources if s.indicator == "sleep_duration")
    data["source"].update(
        dataset_id=req.dataset_id,
        run_id=req.run_id,
        source_id=source.source_id,
        sensor_id=source.sensor_id,
        sensor_epoch=source.sensor_epoch,
        data_origin=req.data_origin,
        metric="sleep_duration",
        unit="h",
        maximum_age_seconds=400000.0,
    )
    return req, result, TemporalPolicy.model_validate(data)


def demonstration() -> dict[str, object]:
    case = synthetic_case()
    temporal = analyze_temporal_evidence(
        case.evidence, policy=case.temporal.policy, assessed_at=case.assessed_at
    )
    _, _, a = context_fixture()
    a_context = adapt_environmental(
        a,
        evidence=case.evidence,
        policy=case.temporal.policy,
        assessed_at=case.assessed_at,
    )
    b_sample = sample()
    b = adapt_model_b(
        service(b_sample).assess(b_sample), assessed_at=b_sample.assessed_at
    )
    req, c_result, c_policy = build_c_case()
    c = adapt_model_c(req, c_result, policy=c_policy, assessed_at=req.assessed_at)
    combined = assess_hybrid(
        case.investigation,
        temporal,
        policy=case.policy,
        assessed_at=case.assessed_at,
        evidence=case.evidence,
        contexts=(a_context, b, c),
    )
    wrong = case.temporal.policy.model_dump()
    wrong["scope"]["astronaut_id"] = "different-synthetic-subject"
    rejected = analyze_temporal_evidence(
        case.evidence,
        policy=TemporalPolicy.model_validate(wrong),
        assessed_at=case.assessed_at,
    )
    replay_case = next(c for c in controlled_cases() if c.name == "F-replay-mismatch")
    replay = adapt_environmental(
        replay_case.contexts[0],
        evidence=replay_case.inputs.evidence,
        policy=replay_case.inputs.temporal.policy,
        assessed_at=replay_case.inputs.assessed_at,
    )
    future_rows = history()
    future_request = request(future_rows)
    future_rows[-1]["temporal_support"]["end"] = future_request.assessed_at + timedelta(
        days=1
    )
    future_request = request(future_rows)
    future = adapt_model_c(
        future_request,
        assess_isolation_confinement(future_request),
        policy=c_policy,
        assessed_at=future_request.assessed_at,
    )
    return {
        "classification": "SYNTHETIC RESEARCH ONLY; Model B uses a fake estimator; not clinical validation",
        "temporal_pattern": temporal.pattern,
        "compatible_hybrid_status": combined.assessment.status,
        "m2_unchanged": combined.assessment.original_investigation
        == case.investigation,
        "cross_subject_status": rejected.pattern,
        "cross_subject_usable_observations": len(rejected.supporting_evidence),
        "historical_replay_eligible": replay.model_context_eligible,
        "historical_replay_reasons": replay.reason_codes,
        "model_b_status": b.native_result.status,
        "model_b_context_only": not b.model_context_eligible,
        "model_c_subject": c_result.subject_id,
        "model_c_temporal_pattern": c.temporal.pattern if c.temporal else None,
        "model_c_context_reasons": c.reason_codes,
        "future_support_excluded": any(
            e.evidence.observation.observation_id == "syn-sleep-w2"
            and any(
                reason in e.reason_codes
                for reason in ("outside_window", "unavailable_at_assessment")
            )
            for e in future.temporal.excluded_evidence
        )
        if future.temporal
        else False,
    }


def main() -> None:
    print(json.dumps(demonstration(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
