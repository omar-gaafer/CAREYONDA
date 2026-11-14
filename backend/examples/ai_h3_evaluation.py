"""AI-H3 offline evaluation harness, not a research algorithm.

Python 3.11+. From backend: PYTHONPATH=. python -m examples.ai_h3_evaluation
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.ai.hazard_reasoning import investigate
from app.ai.research.hybrid import evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.features.temporal_features import SampleAnchor
from app.schemas.baseline import ResearchEvidence
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.hybrid import HybridAssessment, HybridPolicy
from app.schemas.investigation import Investigation
from app.schemas.temporal import TemporalPolicy, TemporalSummary
from examples.hybrid_evidence import SyntheticHybridCase
from examples.hybrid_research_cases import artificial_model_context

SPEC_PATH = (
    Path(__file__).resolve().parents[2] / "docs/research/AI_H3_CHALLENGE_SPEC.json"
)
SPEC_SHA256 = "e77a8f5ed47add63aa35fcf9632d564ec7388dfafcb6519397271139e7fca6a2"
BASELINE = "7b56152c5bad72dd9446f17c301dcc466b16bd6a"


class StrictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Inputs(StrictSpec):
    values: tuple[float, ...] = (2, 2, 2, 2, 2, 2)
    missing: bool = False
    rested: bool = False
    reference_mission: str = "h3-mission"
    reference_subject: str = "h3-subject"
    duplicate: bool = False
    future_reference: bool = False
    require_model: bool = False
    context: Literal["abstained", "replay"] | None = None
    allow_recovery: bool = False
    conflicting_provenance: bool = False
    stale: bool = False


class Expected(StrictSpec):
    temporal_pattern: str | None
    hybrid_status: str | None
    supporting_ids: tuple[str, ...]
    contradicting_ids: tuple[str, ...]


class Challenge(StrictSpec):
    id: str
    inputs: Inputs
    expected: Expected


class Specification(StrictSpec):
    schema_version: Literal["1.0.0"]
    baseline_commit: str
    classification: str
    fixture: dict[str, object]
    cases: tuple[Challenge, ...]


def load_specification(path: Path = SPEC_PATH) -> Specification:
    """Reject expectation changes before any engine is invoked."""
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SPEC_SHA256:
        raise ValueError("challenge specification differs from frozen SHA-256")
    return Specification.model_validate_json(raw)


def evidence(
    identifier: str,
    minute: int,
    value: float,
    *,
    mission: str = "h3-mission",
    subject: str = "h3-subject",
) -> ResearchEvidence:
    """New synthetic fixture, with declared source availability equal to event time."""
    event = datetime(2032, 4, 5, tzinfo=UTC) + timedelta(minutes=minute)
    return ResearchEvidence.model_validate(
        {
            "observation": {
                "schema_version": "1.0.0",
                "observation_id": identifier,
                "timestamp": event,
                "ingested_at": event,
                "domain": "behavioral",
                "metric": "sleep_duration",
                "scope": {
                    "kind": "astronaut",
                    "astronaut_id": subject,
                    "mission_id": mission,
                },
                "measurement": {"kind": "numeric", "value": value, "unit": "h"},
                "quality": {"status": "valid"},
                "provenance": {
                    "source_type": "simulator",
                    "source_id": "h3-source",
                    "method": "synthetic-contract-challenge",
                    "origin": "simulated",
                    "simulation": {
                        "scenario_id": "h3",
                        "run_id": "h3-run",
                        "generator_version": "1.0.0",
                        "seed": 3,
                    },
                },
            },
            "dataset_id": "h3-dataset",
            "run_id": "h3-run",
            "sensor_id": "h3-sensor",
            "sensor_epoch": "epoch-3",
            "data_origin": "synthetic",
            "temporal_support": {"start": event, "end": event},
        }
    )


@dataclass(frozen=True)
class Trial:
    m2: Investigation | None
    temporal: TemporalSummary | None
    hybrid: HybridAssessment | None
    boundary_error: str | None = None

    def serialized(self, configuration: str) -> str:
        """Compare complete native outputs, not just the scored fields."""
        return json.dumps(
            {
                "boundary_error": self.boundary_error,
                "m2": self.m2.model_dump(mode="json") if self.m2 else None,
                "temporal": self.temporal.model_dump(mode="json")
                if self.temporal and configuration != "A"
                else None,
                "hybrid": self.hybrid.model_dump(mode="json")
                if self.hybrid and configuration == "C"
                else None,
            },
            sort_keys=True,
        )


def run_challenge(
    challenge: Challenge,
    *,
    configuration: Literal["A", "B", "C"] = "C",
    reverse: bool = False,
) -> Trial:
    """Call unchanged engines using common raw inputs; never repair rejected evidence."""
    inputs = challenge.inputs
    current = [evidence(f"h3-sleep-{i}", i, v) for i, v in enumerate(inputs.values, 1)]
    start = datetime(2032, 4, 5, tzinfo=UTC)
    end = start + timedelta(minutes=6)
    at = end + timedelta(seconds=121 if inputs.stale else 0)
    if inputs.missing:
        data = current[2].model_dump()
        data["observation"]["measurement"] = {
            "kind": "unavailable",
            "reason": "not_received",
        }
        data["observation"]["quality"] = {
            "status": "missing",
            "reason_codes": ["h3_dropout"],
        }
        current[2] = ResearchEvidence.model_validate(data)
    state_data = current[-1].model_dump()
    state_data["observation"].update(
        observation_id="h3-fatigue",
        metric="fatigue_self_report",
        measurement={
            "kind": "categorical",
            "value": "rested" if inputs.rested else "very_tired",
        },
    )
    state = ResearchEvidence.model_validate(state_data)
    reference = [
        evidence(
            f"h3-reference-{i}",
            i - 10,
            v,
            mission=inputs.reference_mission,
            subject=inputs.reference_subject,
        )
        for i, v in enumerate((7, 8, 9), 1)
    ]
    if inputs.future_reference:
        data = reference[1].model_dump()
        data["observation"]["ingested_at"] = at + timedelta(seconds=1)
        reference[1] = ResearchEvidence.model_validate(data)
    if inputs.duplicate:
        current.append(current[0])
    anchor = SampleAnchor.model_validate(
        {
            "sample_id": "h3-current",
            "episode_id": "h3-episode",
            "mission_id": "h3-mission",
            "astronaut_id": "h3-subject",
            "spacecraft_id": "h3-craft",
            "compartment_id": "h3-compartment",
            "timestamp": end,
        }
    )
    ref_anchor = SampleAnchor.model_validate(
        {
            **anchor.model_dump(),
            "sample_id": "h3-reference",
            "timestamp": start - timedelta(minutes=7),
            "mission_id": inputs.reference_mission,
            "astronaut_id": inputs.reference_subject,
        }
    )
    raw_current = [e.observation for e in (*current, state)]
    raw_reference = [e.observation for e in reference]
    try:
        m2 = investigate(
            list(reversed(raw_current)) if reverse else raw_current,
            anchor,
            list(reversed(raw_reference)) if reverse else raw_reference,
            ref_anchor,
            window_seconds=360,
        )
    except ValueError as error:
        # Only the pre-specified duplicate rejection is an expected boundary outcome.
        # Unexpected validation failures fail the runner, rather than inflating metrics.
        if not inputs.duplicate or str(error) != "duplicate observation IDs":
            raise
        return Trial(None, None, None, "duplicate observation IDs")
    if configuration == "A":
        return Trial(m2, None, None)
    policy = TemporalPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "h3-temporal",
            "policy_version": "1.0.0",
            "scope": current[0].observation.scope,
            "source": {
                "requirement_id": "h3-sleep-source",
                "dataset_id": "h3-dataset",
                "run_id": "h3-run",
                "source_id": "h3-source",
                "sensor_id": "h3-sensor",
                "sensor_epoch": "epoch-3",
                "data_origin": "synthetic",
                "compatibility": "exact_identity",
                "metric": "sleep_duration",
                "unit": "h",
                "maximum_age_seconds": 120,
            },
            "event_window": {"start": start, "end": end},
            "reference_lower": 6,
            "reference_upper": 10,
            "trend_direction": "lower_is_worsening",
            "minimum_slope_per_second": 0.01,
            "minimum_observations": 4,
            "minimum_run": 3,
            "maximum_gap_seconds": 90,
            "convention_reference": "AI_H3_CHALLENGE_SPEC.json; arbitrary synthetic software bounds, no clinical meaning",
        }
    )
    temporal = analyze_temporal_evidence(
        tuple(reversed(current)) if reverse else current, policy=policy, assessed_at=at
    )
    if configuration == "B":
        return Trial(m2, temporal, None)
    hybrid_policy = HybridPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "h3-hybrid",
            "policy_version": "1.0.0",
            "scope": policy.scope,
            "hypothesis_id": "sleep_deprivation",
            "association_mode": "exact_scope_only",
            "maximum_reference_age_seconds": 3600,
            "require_model_context": inputs.require_model,
            "rules": [
                {
                    "rule_id": "h3-sleep",
                    "rule_version": "1.0.0",
                    "source_reference": "AI_H3_CHALLENGE_SPEC.json; M2 sleep_deprivation expectation",
                    "source": policy.source,
                    "expected_relation": "below_reference",
                    "minimum_current_observations": 4,
                    "required_temporal_patterns": [
                        "recovery" if inputs.allow_recovery else "persistent_anomaly"
                    ],
                },
                {
                    "rule_id": "h3-fatigue",
                    "rule_version": "1.0.0",
                    "source_reference": "AI_H3_CHALLENGE_SPEC.json; M2 sleep_deprivation expectation",
                    "source": {
                        **policy.source.model_dump(),
                        "requirement_id": "h3-fatigue-source",
                        "metric": "fatigue_self_report",
                        "unit": "1",
                    },
                    "expected_relation": "fatigue_reported",
                    "minimum_current_observations": 1,
                    "required_temporal_patterns": [],
                },
            ],
        }
    )
    all_evidence = (*current, state, *reference)
    if inputs.conflicting_provenance:
        extra = ResearchEvidence.model_validate(
            {**reference[1].model_dump(), "sensor_id": "h3-conflicting-sensor"}
        )
        all_evidence = (*all_evidence, extra)
    contexts: tuple[EnvironmentalAnomalyContext, ...] = ()
    if inputs.context:
        # Reuse only the declared artificial context constructor, not H2 test cases/oracles.
        contexts = (
            artificial_model_context(
                SyntheticHybridCase(m2, temporal, hybrid_policy, all_evidence, at),
                replay=inputs.context == "replay",
            ),
        )
    hybrid = evaluate_hybrid_evidence(
        m2,
        temporal,
        policy=hybrid_policy,
        assessed_at=at,
        m2_evidence=tuple(reversed(all_evidence)) if reverse else all_evidence,
        model_contexts=contexts,
    )
    return Trial(m2, temporal, hybrid)


def score(challenge: Challenge, trial: Trial) -> dict[str, object]:
    """Score against the frozen oracle, never derive expected sets from predictions."""
    if trial.boundary_error:
        return {
            "case": challenge.id,
            "eligible": False,
            "boundary_error": trial.boundary_error,
            "expected_boundary_rejection": challenge.inputs.duplicate,
        }
    m2, temporal, hybrid = trial.m2, trial.temporal, trial.hybrid
    assert m2 is not None and temporal is not None and hybrid is not None
    expected = challenge.expected
    support, contra = (
        set(hybrid.supporting_evidence_ids),
        set(hybrid.contradicting_evidence_ids),
    )
    expected_support, expected_contra = (
        set(expected.supporting_ids),
        set(expected.contradicting_ids),
    )
    abstaining = expected.hybrid_status in {
        "insufficient_evidence",
        "incompatible_evidence",
    }
    actual_abstaining = hybrid.status in {
        "insufficient_evidence",
        "incompatible_evidence",
    }
    directional = [
        step
        for step in hybrid.reasoning_steps
        if step.outcome in {"supports", "contradicts"}
    ]
    references = [
        oid
        for step in directional
        for oid in (*step.evidence_ids, *step.reference_evidence_ids)
    ]
    snapshots = {e.observation.observation_id for e in hybrid.evidence_snapshots}
    target = next(h for h in m2.hypotheses if h.hypothesis_id == "sleep_deprivation")
    return {
        "case": challenge.id,
        "eligible": True,
        "expected": expected.model_dump(mode="json"),
        "A": {
            "status": m2.status,
            "selected_hypothesis": m2.selected_hypothesis,
            "ranks": [[h.hypothesis_id, h.rank] for h in m2.hypotheses],
            "target_findings": target.model_dump(mode="json"),
            "sha256": sha256(m2.model_dump_json().encode()).hexdigest(),
        },
        "B": {
            "temporal_pattern": temporal.pattern,
            "abstention_reasons": temporal.abstention_reasons,
            "valid_count": temporal.valid_observation_count,
        },
        "C": {
            "status": hybrid.status,
            "supporting_ids": sorted(support),
            "contradicting_ids": sorted(contra),
            "abstention_reasons": hybrid.abstention_reasons,
            "reasoning_steps": [
                s.model_dump(mode="json") for s in hybrid.reasoning_steps
            ],
            "model_reasoning_steps": [
                s.model_dump(mode="json") for s in hybrid.model_reasoning_steps
            ],
            "snapshot_ids": sorted(snapshots),
        },
        "association_correct": hybrid.status == expected.hybrid_status
        and support == expected_support
        and contra == expected_contra,
        "contradiction_correct": contra == expected_contra if expected_contra else None,
        "abstention_correct": abstaining == actual_abstaining
        and bool(hybrid.abstention_reasons) == abstaining,
        "unsupported_directional_assertions": len(support - expected_support)
        + len(contra - expected_contra),
        "traced_references": sum(oid in snapshots for oid in references),
        "directional_references": len(references),
        "temporal_correct": temporal.pattern == expected.temporal_pattern,
        "m2_unchanged": hybrid.original_investigation == m2,
    }


def evaluation_report() -> dict[str, object]:
    """Return reproducible ablation results; N/A is explicit and denominators visible."""
    spec = load_specification()
    rows: list[dict[str, object]] = []
    configurations: tuple[Literal["A", "B", "C"], ...] = ("A", "B", "C")
    determinism = {name: 0 for name in configurations}
    for challenge in spec.cases:
        trials = {
            name: run_challenge(challenge, configuration=name)
            for name in configurations
        }
        row = score(challenge, trials["C"])
        checks: dict[str, bool] = {}
        for name in configurations:
            repeated = run_challenge(challenge, configuration=name)
            reversed_trial = run_challenge(challenge, configuration=name, reverse=True)
            checks[name] = (
                trials[name].serialized(name)
                == repeated.serialized(name)
                == reversed_trial.serialized(name)
            )
            determinism[name] += checks[name]
        row["determinism"] = checks
        if row["eligible"]:
            row["m2_unchanged"] = (
                row["m2_unchanged"]
                and trials["A"].m2 == trials["B"].m2 == trials["C"].m2
            )
            row["temporal_unchanged"] = trials["B"].temporal == trials["C"].temporal
        rows.append(row)
    eligible = [row for row in rows if row["eligible"]]

    def fraction(key: str) -> dict[str, int]:
        applicable = [row for row in eligible if row[key] is not None]
        return {
            "correct": sum(row[key] is True for row in applicable),
            "total": len(applicable),
        }

    def total(key: str) -> int:
        values = [row[key] for row in eligible]
        assert all(isinstance(value, int) for value in values)
        return sum(value for value in values if isinstance(value, int))

    na = {
        "value": None,
        "reason": "N/A: configuration does not emit this research sidecar contract",
    }
    metrics: dict[str, object] = {}
    for name in determinism:
        metrics[name] = {
            "evidence_association_correctness": fraction("association_correct")
            if name == "C"
            else na,
            "contradiction_handling": fraction("contradiction_correct")
            if name == "C"
            else na,
            "abstention_correctness": fraction("abstention_correct")
            if name == "C"
            else na,
            "unsupported_directional_assertions": total(
                "unsupported_directional_assertions"
            )
            if name == "C"
            else na,
            "provenance_trace_completeness": {
                "resolved": total("traced_references"),
                "total": total("directional_references"),
            }
            if name == "C"
            else na,
            "temporal_pattern_recognition": fraction("temporal_correct")
            if name != "A"
            else na,
            "deterministic_reproducibility": {
                "correct": determinism[name],
                "total": len(rows),
            },
        }
    return {
        "schema_version": "1.0.0",
        "baseline_commit": BASELINE,
        "specification_sha256": SPEC_SHA256,
        "interpretation": spec.classification,
        "development_cases": {
            "count": 12,
            "source": "examples.hybrid_research_cases",
            "included_in_challenge_metrics": False,
        },
        "challenge_count": len(rows),
        "eligible_count": len(eligible),
        "boundary_rejections": len(rows) - len(eligible),
        "m2_invariance": fraction("m2_unchanged"),
        "metrics": metrics,
        "cases": rows,
    }


if __name__ == "__main__":
    print(json.dumps(evaluation_report(), indent=2, sort_keys=True))
