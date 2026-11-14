"""Reproducible SYNTHETIC research comparison; no clinical or NASA data.

From backend: PYTHONPATH=. python -m examples.hybrid_evidence
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.ai.hazard_reasoning import investigate
from app.ai.research.hybrid import evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.features.temporal_features import SampleAnchor
from app.schemas.baseline import ResearchEvidence
from app.schemas.hybrid import HybridAssessment, HybridPolicy
from app.schemas.investigation import Investigation
from app.schemas.temporal import TemporalSummary
from examples.temporal_evidence import synthetic_evidence, synthetic_policy


@dataclass(frozen=True)
class SyntheticHybridCase:
    investigation: Investigation
    temporal: TemporalSummary
    policy: HybridPolicy
    evidence: tuple[ResearchEvidence, ...]
    assessed_at: datetime

    def evaluate(self) -> HybridAssessment:
        return evaluate_hybrid_evidence(
            self.investigation,
            self.temporal,
            policy=self.policy,
            assessed_at=self.assessed_at,
            m2_evidence=self.evidence,
        )


def synthetic_case(
    values: list[float] | None = None,
    *,
    active: bool = True,
    reference_value: float = 5.0,
    missing_index: int | None = None,
    stale: bool = False,
    allow_recovery: bool = False,
) -> SyntheticHybridCase:
    """Arbitrary reference and observations exercise M2/AI-H1/AI-H2 interfaces."""
    if values is None:
        values = [20.0, 20.0, 20.0, 20.0, 20.0]
    current = list(synthetic_evidence(values))
    if missing_index is not None:
        data = current[missing_index].model_dump()
        data["observation"]["measurement"] = {
            "kind": "unavailable",
            "reason": "not_received",
        }
        data["observation"]["quality"] = {
            "status": "missing",
            "reason_codes": ["synthetic_dropout"],
        }
        current[missing_index] = ResearchEvidence.model_validate(data)
    reference = []
    for e in synthetic_evidence([reference_value] * 3):
        data = e.model_dump()
        event = e.observation.timestamp - timedelta(minutes=10)
        data["observation"].update(
            observation_id="reference-" + e.observation.observation_id,
            timestamp=event,
            ingested_at=event,
        )
        data["temporal_support"] = {"start": event, "end": event}
        reference.append(ResearchEvidence.model_validate(data))
    p = synthetic_policy(len(values))
    state = current[-1].model_dump()
    state["observation"].update(
        observation_id="synthetic-exercise",
        domain="mission_context",
        metric="exercise_active",
        measurement={"kind": "boolean", "value": active},
        quality={"status": "valid"},
    )
    exercise = ResearchEvidence.model_validate(state)
    current_anchor = SampleAnchor.model_validate(
        {
            "sample_id": "synthetic-current",
            "episode_id": "synthetic-episode",
            "mission_id": "synthetic-mission",
            "astronaut_id": "synthetic-subject",
            "spacecraft_id": "synthetic-craft",
            "compartment_id": "synthetic-compartment",
            "timestamp": p.event_window.end,
        }
    )
    reference_anchor = SampleAnchor.model_validate(
        {
            **current_anchor.model_dump(),
            "sample_id": "synthetic-reference",
            "timestamp": reference[-1].observation.timestamp,
        }
    )
    m2 = investigate(
        [e.observation for e in (*current, exercise)],
        current_anchor,
        [e.observation for e in reference],
        reference_anchor,
        window_seconds=60 * len(values),
    )
    temporal = analyze_temporal_evidence(
        current, policy=p, assessed_at=p.event_window.end
    )
    policy = HybridPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "synthetic-hybrid",
            "policy_version": "1.0.0",
            "scope": p.scope,
            "hypothesis_id": "recent_exercise",
            "association_mode": "exact_scope_only",
            "maximum_reference_age_seconds": 3600.0,
            "require_model_context": False,
            "rules": [
                {
                    "rule_id": "synthetic-heart-sequence",
                    "rule_version": "1.0.0",
                    "source_reference": "Synthetic research case specification; M2 recent_exercise heart_rate expectation",
                    "source": p.source,
                    "expected_relation": "above_reference",
                    "minimum_current_observations": 3,
                    "required_temporal_patterns": ["recovery"]
                    if allow_recovery
                    else ["persistent_anomaly"],
                },
                {
                    "rule_id": "synthetic-exercise-state",
                    "rule_version": "1.0.0",
                    "source_reference": "Synthetic research case specification; M2 recent_exercise active expectation",
                    "source": {
                        **p.source.model_dump(),
                        "requirement_id": "synthetic-exercise-source",
                        "metric": "exercise_active",
                        "unit": "1",
                    },
                    "expected_relation": "active",
                    "minimum_current_observations": 1,
                    "required_temporal_patterns": [],
                },
            ],
        }
    )
    return SyntheticHybridCase(
        m2,
        temporal,
        policy,
        (*current, exercise, *reference),
        p.event_window.end + timedelta(seconds=121 if stale else 0),
    )


if __name__ == "__main__":
    for name, case in (
        ("A-persistent", synthetic_case()),
        ("B-isolated", synthetic_case([5.0, 5.0, 20.0, 5.0, 5.0])),
        ("C-conflict", synthetic_case(active=False)),
        ("D-missing", synthetic_case(missing_index=2)),
        ("D-stale", synthetic_case(stale=True)),
        (
            "J-statistical-return",
            synthetic_case([20.0, 20.0, 5.0, 5.0], allow_recovery=True),
        ),
    ):
        assessment = case.evaluate()
        print(
            name,
            {
                "original_m2": case.investigation.status,
                "original_ranks": [
                    (h.hypothesis_id, h.rank) for h in case.investigation.hypotheses
                ],
                "temporal_sidecar": case.temporal.pattern,
                "hybrid_research_status": assessment.status,
                "supporting_ids": assessment.supporting_evidence_ids,
                "contradicting_ids": assessment.contradicting_evidence_ids,
                "abstention_reasons": assessment.abstention_reasons,
            },
        )
