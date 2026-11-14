"""Independently specified SYNTHETIC AI-H2 oracle and reproducible research cases.

No NASA values or model artifacts. Model contexts below are declared fixtures,
not scores from a fitted model. Run from backend: python -m examples.hybrid_research_cases
"""

import json
from dataclasses import dataclass, replace
from datetime import timedelta

from app.ai.research.hybrid import evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.features.environmental import build_environment_features, environmental_schema
from app.schemas.baseline import ResearchEvidence
from app.schemas.environmental_anomaly_context import (
    LIMITATIONS,
    REPLAY_LIMITATIONS,
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
)
from app.schemas.hybrid import HybridAssessment, HybridPolicy, ResearchStatus
from app.schemas.observation import Observation
from app.schemas.temporal import TemporalPolicy
from examples.hybrid_evidence import SyntheticHybridCase, synthetic_case


@dataclass(frozen=True)
class ControlledCase:
    name: str
    inputs: SyntheticHybridCase
    expected_status: ResearchStatus
    expected_supporting: frozenset[str]
    expected_contradicting: frozenset[str]
    contexts: tuple[EnvironmentalAnomalyContext, ...] = ()

    def evaluate(self, *, reverse_evidence: bool = False) -> HybridAssessment:
        case = self.inputs
        return evaluate_hybrid_evidence(
            case.investigation,
            case.temporal,
            policy=case.policy,
            assessed_at=case.assessed_at,
            m2_evidence=tuple(reversed(case.evidence))
            if reverse_evidence
            else case.evidence,
            model_contexts=self.contexts,
        )


def artificial_model_context(
    case: SyntheticHybridCase,
    *,
    replay: bool = False,
    flagged: bool = False,
    not_flagged: bool = False,
) -> EnvironmentalAnomalyContext:
    """Synthetic contract fixture only: no NASA data, model execution or fitted scores."""
    observations = []
    for metric, unit, value in (
        ("cabin_co2_concentration", "ppm", 100.0),
        ("environment_temperature", "degC", 10.0),
        ("relative_humidity", "%", 20.0),
    ):
        data = case.temporal.supporting_evidence[-1].observation.model_dump()
        data.update(
            observation_id="synthetic-env-" + metric,
            domain="environmental",
            metric=metric,
            scope={
                "kind": "spacecraft",
                "spacecraft_id": "ISS",
                "mission_id": "NASA-RR1",
            },
            measurement={"kind": "numeric", "value": value, "unit": unit},
        )
        if replay:
            data["ingested_at"] = None
        observations.append(Observation.model_validate(data))
    built = build_environment_features(observations)[0]
    schema = environmental_schema()["features"]
    assert isinstance(schema, list)
    sample = EnvironmentalSample.model_validate(
        {
            "sample_id": "synthetic-model-context",
            "scope": {
                "mission_id": "NASA-RR1",
                "spacecraft_id": "ISS",
                "data_origin": "synthetic",
                "dataset_id": "synthetic-dataset",
                "run_id": "synthetic-run",
            },
            "event_time_utc": case.temporal.policy.event_window.end,
            "available_at": None if replay else case.assessed_at,
            "assessment_mode": "historical_replay" if replay else "live",
            "historical_source_availability": "unknown" if replay else "known",
            "replay_acquired_at": case.assessed_at if replay else None,
            "replay_acquisition": {
                "record_id": "synthetic-receipt",
                "dataset_id": "synthetic-dataset",
                "dataset_manifest_sha256": "0" * 64,
                "acquired_at": case.assessed_at,
                "source_reference": "Synthetic replay receipt fixture only",
            }
            if replay
            else None,
            "transformation_version": "environmental-1.0.0",
            "observations": observations,
            "features": [
                {
                    "name": f["name"],
                    "unit": f["unit"],
                    "value": built.values[f["name"]],
                    "observation_ids": built.evidence[f["name"]],
                }
                for f in schema
            ],
        }
    )
    scored = flagged or not_flagged
    return EnvironmentalAnomalyContext.model_validate(
        {
            "sample": sample,
            "assessed_at": case.assessed_at,
            "assessment_mode": sample.assessment_mode,
            "historical_source_availability": sample.historical_source_availability,
            "replay_acquired_at": sample.replay_acquired_at,
            "source_event_time": sample.event_time_utc,
            "evidence_availability_scope": "careyonda_replay"
            if replay
            else "source_stream",
            "model": {
                "model_id": "careyonda-model-a-nasa-rr1-environment-iforest",
                "model_version": "1.1.0",
                "feature_schema_version": "1.0.0",
                "artifact_sha256": "0" * 64,
                "dataset_manifest_sha256": "0" * 64,
            }
            if scored
            else None,
            "availability": "available" if scored else "unavailable",
            "compatibility": "compatible" if scored else "unknown",
            "status": "flagged"
            if flagged
            else "not_flagged"
            if not_flagged
            else "abstained",
            "anomaly_score": 0.7 if flagged else 0.1 if not_flagged else None,
            "threshold": 0.5 if scored else None,
            "threshold_method": "training_score_quantile" if scored else None,
            "imputed_features": [],
            "abstention_reasons": [] if scored else ["synthetic_model_unavailable"],
            "limitations": (*LIMITATIONS, *REPLAY_LIMITATIONS)
            if replay
            else LIMITATIONS,
        }
    )


def controlled_cases() -> tuple[ControlledCase, ...]:
    """Expectations below are authored from case definitions, not engine predictions."""
    heart = frozenset(f"synthetic-{i}" for i in range(1, 6))
    state = frozenset({"synthetic-exercise"})
    base = synthetic_case()
    required = HybridPolicy.model_validate(
        {**base.policy.model_dump(), "require_model_context": True}
    )
    cross_subject = []
    for e in base.temporal.supporting_evidence:
        data = e.model_dump()
        data["observation"]["scope"]["astronaut_id"] = "other-subject"
        cross_subject.append(ResearchEvidence.model_validate(data))
    tp = TemporalPolicy.model_validate(
        {
            **base.temporal.policy.model_dump(),
            "scope": {
                **base.temporal.policy.scope.model_dump(),
                "astronaut_id": "other-subject",
            },
        }
    )
    other = analyze_temporal_evidence(
        cross_subject, policy=tp, assessed_at=base.assessed_at
    )
    future_evidence = []
    for e in base.evidence:
        data = e.model_dump()
        if e.observation.observation_id == "synthetic-3":
            data["observation"]["ingested_at"] = base.assessed_at + timedelta(seconds=1)
        future_evidence.append(ResearchEvidence.model_validate(data))
    future_temporal = analyze_temporal_evidence(
        future_evidence[:5], policy=base.temporal.policy, assessed_at=base.assessed_at
    )
    recovery = synthetic_case([20.0, 20.0, 5.0, 5.0], allow_recovery=True)
    return (
        ControlledCase(
            "A-persistent",
            base,
            "supported_by_available_evidence",
            heart | state,
            frozenset(),
        ),
        ControlledCase(
            "B-isolated",
            synthetic_case([5.0, 5.0, 20.0, 5.0, 5.0]),
            "insufficient_evidence",
            state,
            frozenset(),
        ),
        ControlledCase(
            "C-conflicting",
            synthetic_case(active=False),
            "mixed_evidence",
            heart,
            state,
        ),
        ControlledCase(
            "D-missing",
            synthetic_case(missing_index=2),
            "insufficient_evidence",
            state,
            frozenset(),
        ),
        ControlledCase(
            "D-stale",
            synthetic_case(stale=True),
            "insufficient_evidence",
            frozenset(),
            frozenset(),
        ),
        ControlledCase(
            "E-other-subject",
            replace(base, temporal=other),
            "incompatible_evidence",
            state,
            frozenset(),
        ),
        ControlledCase(
            "F-replay-mismatch",
            replace(base, policy=required),
            "insufficient_evidence",
            heart | state,
            frozenset(),
            (artificial_model_context(base, replay=True),),
        ),
        ControlledCase(
            "G-model-abstention",
            replace(base, policy=required),
            "insufficient_evidence",
            heart | state,
            frozenset(),
            (artificial_model_context(base),),
        ),
        ControlledCase(
            "H-future-unavailable",
            replace(base, evidence=tuple(future_evidence), temporal=future_temporal),
            "insufficient_evidence",
            state,
            frozenset(),
        ),
        ControlledCase(
            "I-duplicate-provenance",
            replace(base, evidence=(*base.evidence, base.evidence[0])),
            "incompatible_evidence",
            state,
            frozenset(),
        ),
        ControlledCase(
            "J-statistical-return",
            recovery,
            "supported_by_available_evidence",
            frozenset(
                {
                    "synthetic-1",
                    "synthetic-2",
                    "synthetic-3",
                    "synthetic-4",
                    "synthetic-exercise",
                }
            ),
            frozenset(),
        ),
        ControlledCase(
            "C-all-contradict",
            synthetic_case(active=False, reference_value=30.0),
            "contradicted_by_available_evidence",
            frozenset(),
            heart | state,
        ),
    )


def evaluation_report() -> dict[str, object]:
    """Software association metrics over a finite, independently declared oracle."""
    rows = []
    correct = unsupported = abstentions = correct_abstentions = 0
    traced = directional = deterministic = 0
    expected_conflicts = correct_conflicts = reference_traced = reference_count = 0
    for case in controlled_cases():
        result = case.evaluate()
        support, contra = (
            set(result.supporting_evidence_ids),
            set(result.contradicting_evidence_ids),
        )
        correct += (
            support == case.expected_supporting
            and contra == case.expected_contradicting
            and result.status == case.expected_status
        )
        if case.expected_contradicting:
            expected_conflicts += 1
            correct_conflicts += contra == case.expected_contradicting
        unsupported += len(support - case.expected_supporting) + len(
            contra - case.expected_contradicting
        )
        should_abstain = case.expected_status in {
            "insufficient_evidence",
            "incompatible_evidence",
        }
        abstentions += should_abstain
        correct_abstentions += should_abstain and bool(result.abstention_reasons)
        snapshots = {e.observation.observation_id for e in result.evidence_snapshots}
        for step in result.reasoning_steps:
            if step.outcome in {"supports", "contradicts"}:
                directional += len(step.evidence_ids)
                traced += sum(oid in snapshots for oid in step.evidence_ids)
                reference_count += len(step.reference_evidence_ids)
                reference_traced += sum(
                    oid in snapshots for oid in step.reference_evidence_ids
                )
        deterministic += (
            result.model_dump_json()
            == case.evaluate(reverse_evidence=True).model_dump_json()
        )
        rows.append(
            {
                "case": case.name,
                "original_m2_status": result.original_investigation.status,
                "original_m2_ranks": [
                    (h.hypothesis_id, h.rank)
                    for h in result.original_investigation.hypotheses
                ],
                "m2_with_temporal_pattern": result.temporal_summary.pattern,
                "hybrid_status": result.status,
                "expected_status": case.expected_status,
                "supporting_ids": sorted(support),
                "contradicting_ids": sorted(contra),
                "expected_supporting_ids": sorted(case.expected_supporting),
                "expected_contradicting_ids": sorted(case.expected_contradicting),
                "m2_with_temporal_ranks_unchanged": result.original_investigation
                == case.inputs.investigation,
                "missing_evidence": result.missing_evidence,
                "abstention_reasons": result.abstention_reasons,
                "model_exclusion_reasons": sorted(
                    {
                        reason
                        for step in result.model_reasoning_steps
                        for reason in step.reason_codes
                    }
                ),
            }
        )
    return {
        "interpretation": "synthetic software association only; no clinical or operational accuracy",
        "case_count": len(rows),
        "correct_association_cases": correct,
        "unsupported_directional_assertions": unsupported,
        "expected_contradicting_cases": expected_conflicts,
        "correct_contradiction_cases": correct_conflicts,
        "reference_evidence_references": reference_count,
        "traced_reference_evidence_references": reference_traced,
        "expected_abstaining_cases": abstentions,
        "correct_abstaining_cases": correct_abstentions,
        "directional_evidence_references": directional,
        "traced_directional_references": traced,
        "deterministic_cases": deterministic,
        "cases": rows,
    }


if __name__ == "__main__":
    print(json.dumps(evaluation_report(), indent=2))
