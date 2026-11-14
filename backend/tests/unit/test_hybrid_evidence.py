"""Synthetic public-interface tests; expected relationships are independently authored."""

from dataclasses import replace
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.ai.research.hybrid import HybridInputError, evaluate_hybrid_evidence
from app.schemas.baseline import ResearchEvidence
from app.schemas.hybrid import HybridAssessment, HybridPolicy
from app.schemas.investigation import Investigation
from app.schemas.temporal import TemporalSummary
from examples.hybrid_evidence import synthetic_case
from examples.hybrid_research_cases import (
    ControlledCase,
    controlled_cases,
    evaluation_report,
)


@pytest.mark.parametrize("case", controlled_cases(), ids=lambda c: c.name)
def test_controlled_oracle(case: ControlledCase) -> None:
    result = case.evaluate()
    assert result.status == case.expected_status
    assert set(result.supporting_evidence_ids) == case.expected_supporting
    assert set(result.contradicting_evidence_ids) == case.expected_contradicting
    assert HybridAssessment.model_validate_json(result.model_dump_json()) == result
    assert (
        result.model_dump_json()
        == case.evaluate(reverse_evidence=True).model_dump_json()
    )
    assert result.original_investigation == case.inputs.investigation


def test_independent_research_metrics() -> None:
    r = evaluation_report()
    assert r["correct_association_cases"] == r["case_count"] == 12
    assert r["unsupported_directional_assertions"] == 0
    assert r["expected_abstaining_cases"] == r["correct_abstaining_cases"] == 8
    assert (
        r["traced_directional_references"] == r["directional_evidence_references"] == 40
    )
    assert r["deterministic_cases"] == 12
    assert r["expected_contradicting_cases"] == r["correct_contradiction_cases"] == 2
    assert (
        r["reference_evidence_references"]
        == r["traced_reference_evidence_references"]
        == 18
    )


@pytest.mark.parametrize(
    "field", ["mission", "subject", "sensor", "epoch", "dataset", "run", "source"]
)
def test_reference_context_mismatch(field: str) -> None:
    c = synthetic_case()
    changed = []
    for e in c.evidence:
        data = e.model_dump()
        if e.observation.observation_id.startswith("reference-"):
            if field in {"mission", "subject"}:
                data["observation"]["scope"][
                    "mission_id" if field == "mission" else "astronaut_id"
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
        changed.append(ResearchEvidence.model_validate(data))
    r = replace(c, evidence=tuple(changed)).evaluate()
    assert r.status == "incompatible_evidence"
    assert "scope_or_source_mismatch" in r.abstention_reasons
    assert not set(r.supporting_evidence_ids) & {f"synthetic-{i}" for i in range(1, 6)}


@pytest.mark.parametrize("kind", ["missing", "late", "unknown", "invalid", "stale"])
def test_reference_limitations_abstain(kind: str) -> None:
    c = synthetic_case()
    changed = []
    for e in c.evidence:
        data = e.model_dump()
        if e.observation.observation_id.startswith("reference-"):
            if kind == "missing":
                continue
            if kind in {"late", "unknown"}:
                data["observation"]["ingested_at"] = (
                    c.assessed_at + timedelta(seconds=1) if kind == "late" else None
                )
            if kind == "invalid":
                data["observation"]["quality"] = {
                    "status": "invalid",
                    "reason_codes": ["synthetic_invalid"],
                }
        changed.append(ResearchEvidence.model_validate(data))
    policy = c.policy
    if kind == "stale":
        policy = HybridPolicy.model_validate(
            {**policy.model_dump(), "maximum_reference_age_seconds": 1.0}
        )
    r = replace(c, evidence=tuple(changed), policy=policy).evaluate()
    assert r.status == "insufficient_evidence"
    assert "heart_rate" in r.missing_evidence


@pytest.mark.parametrize(
    "kind", ["value", "relation", "duplicate", "unbound", "state_value"]
)
def test_inconsistent_m2_finding_quarantined(kind: str) -> None:
    c = synthetic_case()
    data = c.investigation.model_dump()
    target = next(
        h for h in data["hypotheses"] if h["hypothesis_id"] == "recent_exercise"
    )
    finding = next(
        f
        for f in target["supporting_evidence"]
        if f["metric"] == ("exercise_active" if kind == "state_value" else "heart_rate")
    )
    if kind in {"value", "state_value"}:
        finding["observed_value"] = 999.0
    elif kind == "relation":
        finding["relation"] = "below_reference"
    elif kind == "duplicate":
        finding["observation_ids"] = (
            *finding["observation_ids"],
            finding["observation_ids"][0],
        )
    else:
        data["observation_ids"] = tuple(
            i for i in data["observation_ids"] if i != finding["observation_ids"][0]
        )
    r = replace(c, investigation=Investigation.model_validate(data)).evaluate()
    assert r.status == "incompatible_evidence"
    assert r.abstention_reasons


def test_derived_provenance_is_not_authenticated_by_parent_ids() -> None:
    c = synthetic_case()
    changed = []
    for e in c.evidence:
        data = e.model_dump()
        if e.observation.observation_id.startswith("reference-"):
            data["observation"]["provenance"].update(
                origin="derived",
                source_type="computation",
                simulation=None,
                parent_observation_ids=("unresolved-parent",),
                transformation_version="synthetic-1",
            )
        changed.append(ResearchEvidence.model_validate(data))
    r = replace(c, evidence=tuple(changed)).evaluate()
    assert "derived_provenance_unverified" in r.abstention_reasons
    assert r.status == "incompatible_evidence"


def test_conflicting_provenance_same_id_quarantined() -> None:
    c = synthetic_case()
    data = c.evidence[0].model_dump()
    data["observation"]["provenance"]["method"] = "other-transform"
    changed = ResearchEvidence.model_validate(data)
    r = replace(c, evidence=(changed, *c.evidence[1:])).evaluate()
    assert r.status == "incompatible_evidence"
    assert "duplicate_or_conflicting_provenance" in r.abstention_reasons


def test_forged_temporal_pattern_is_rejected() -> None:
    c = synthetic_case()
    t = TemporalSummary.model_validate(
        {**c.temporal.model_dump(), "pattern": "recovery"}
    )
    with pytest.raises(HybridInputError, match="reconstruction"):
        replace(c, temporal=t).evaluate()


def test_policy_must_follow_original_m2_expectation() -> None:
    c = synthetic_case()
    data = c.policy.model_dump()
    data["rules"][0]["expected_relation"] = "below_reference"
    r = replace(c, policy=HybridPolicy.model_validate(data)).evaluate()
    assert r.status == "incompatible_evidence"
    assert "policy_m2_expectation_mismatch" in r.abstention_reasons


def test_missing_rule_cannot_support_whole_hypothesis() -> None:
    c = synthetic_case()
    data = c.policy.model_dump()
    data["rules"] = data["rules"][:1]
    r = replace(c, policy=HybridPolicy.model_validate(data)).evaluate()
    assert r.status == "insufficient_evidence"
    assert r.missing_evidence == ("exercise_active",)
    assert "missing_association_rule" in r.abstention_reasons


def test_temporal_summary_assessment_cannot_look_ahead() -> None:
    c = synthetic_case()
    r = replace(c, assessed_at=c.assessed_at - timedelta(seconds=1)).evaluate()
    assert r.status == "insufficient_evidence"
    assert "temporal_summary_unavailable_at_assessment" in r.abstention_reasons


def test_physical_invalidity_is_not_temporal_support() -> None:
    r = synthetic_case([-20.0] * 5).evaluate()
    assert r.status != "supported_by_available_evidence"
    assert "nonvalid_evidence" in r.abstention_reasons


def test_temporal_only_cannot_resolve_missing_m2_reference() -> None:
    c = synthetic_case()
    r = evaluate_hybrid_evidence(
        c.investigation,
        c.temporal,
        policy=c.policy,
        assessed_at=c.assessed_at,
        m2_evidence=(),
    )
    assert r.status == "insufficient_evidence"
    assert "missing_original_evidence" in r.abstention_reasons


@pytest.mark.parametrize(
    "kind",
    ["naive_time", "units", "policy_duplicates", "no_temporal_rule", "schema", "extra"],
)
def test_boundary_validation(kind: str) -> None:
    c = synthetic_case()
    if kind == "naive_time":
        with pytest.raises(ValidationError):
            replace(c, assessed_at=c.assessed_at.replace(tzinfo=None)).evaluate()
        return
    data = c.policy.model_dump()
    if kind == "units":
        data["rules"][0]["source"]["unit"] = "Hz"
    elif kind == "policy_duplicates":
        data["rules"] = (*data["rules"], data["rules"][0])
    elif kind == "no_temporal_rule":
        data["rules"][0]["required_temporal_patterns"] = ()
    elif kind == "schema":
        data["schema_version"] = "9.0.0"
    else:
        data["clinical_confidence"] = 1.0
    with pytest.raises(ValidationError):
        HybridPolicy.model_validate(data)


def test_assessment_output_rejects_invented_lineage() -> None:
    r = synthetic_case().evaluate()
    with pytest.raises(ValidationError):
        HybridAssessment.model_validate(
            {**r.model_dump(), "supporting_evidence_ids": ("invented",)}
        )


def test_determinism_and_input_immutability() -> None:
    c = synthetic_case()
    before = (
        c.investigation.model_dump_json(),
        c.temporal.model_dump_json(),
        c.policy.model_dump_json(),
    )
    r = c.evaluate()
    assert before == (
        c.investigation.model_dump_json(),
        c.temporal.model_dump_json(),
        c.policy.model_dump_json(),
    )
    assert r.model_dump_json() == c.evaluate().model_dump_json()
    assert r.original_investigation.model_dump_json() == before[0]
    assert r.assessed_at.utcoffset() == timedelta(0)
