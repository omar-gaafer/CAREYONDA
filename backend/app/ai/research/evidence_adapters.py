"""Research-only boundary adapters. No new inference, unit conversion or clocks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.ai.research.hybrid import evaluate_hybrid_evidence
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.baseline import ResearchEvidence, TimeInterval
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.hybrid import HybridAssessment, HybridPolicy
from app.schemas.investigation import Investigation
from app.schemas.isolation_confinement import (
    IsolationConfinementAssessment,
    ModelCRequest,
    NumericIndicatorAssessment,
)
from app.schemas.model_b import ModelBFinding
from app.schemas.temporal import TemporalPolicy, TemporalSummary

NativeContext = (
    EnvironmentalAnomalyContext | ModelBFinding | IsolationConfinementAssessment
)


class ResearchAdapterError(ValueError):
    """Invalid original-result/evidence binding; no sensitive input in message."""


@dataclass(frozen=True)
class ContextAdaptation:
    native_result: NativeContext
    temporal: TemporalSummary | None
    model_context_eligible: bool
    reason_codes: tuple[str, ...]
    model_c_request: ModelCRequest | None = None
    limitations: tuple[str, ...] = (
        "Research only; original model scores are not clinical probabilities or hazard direction.",
        "Availability is validated against original declarations, not independently authenticated.",
        "Context-only findings never supply directional M2 evidence.",
    )


@dataclass(frozen=True)
class AdaptedHybridAssessment:
    assessment: HybridAssessment
    contexts: tuple[ContextAdaptation, ...]


def adapt_environmental(
    context: EnvironmentalAnomalyContext,
    *,
    evidence: Sequence[ResearchEvidence],
    policy: TemporalPolicy,
    assessed_at: datetime,
) -> ContextAdaptation:
    """Only original live evidence can use the existing Model A H1 context path."""
    assessed_at = TimeInterval(start=assessed_at, end=assessed_at).end
    original = EnvironmentalAnomalyContext.model_validate(context.model_dump())
    if original.assessment_mode != "live":
        return ContextAdaptation(
            original, None, False, ("historical_replay_not_prospective",)
        )
    summary = analyze_temporal_evidence(
        evidence, policy=policy, assessed_at=assessed_at, model_contexts=(original,)
    )
    trace = summary.model_contexts[0]
    return ContextAdaptation(original, summary, trace.used, trace.reason_codes)


def adapt_model_b(
    finding: ModelBFinding, *, assessed_at: datetime
) -> ContextAdaptation:
    """B has no native H1/H2 context type. Preserve the complete v2 finding only.

    Feature aggregates and imputed values are never reconstructed as raw readings.
    Unassessed is not mapped to normal/not-flagged. No policy is selected here.
    """
    assessed_at = TimeInterval(start=assessed_at, end=assessed_at).end
    original = ModelBFinding.model_validate(finding.model_dump())
    reasons = ["model_b_native_context_only"]
    if original.status in {"unassessed", "abstained"}:
        reasons.append("model_b_" + original.status)
    if original.sample.availability_mode != "prospective":
        reasons.append("retrospective_not_prospective")
    if original.sample.assessed_at > assessed_at:
        reasons.append("context_unavailable_at_assessment")
    return ContextAdaptation(original, None, False, tuple(reasons))


def adapt_model_c(
    request: ModelCRequest,
    result: IsolationConfinementAssessment,
    *,
    policy: TemporalPolicy | None,
    assessed_at: datetime,
) -> ContextAdaptation:
    """C scores/counts stay native. Only original sleep observations may enter H1.

    The caller must supply an explicit reviewed numeric research policy; this
    adapter never derives reference bounds from MAD, scores or fatigue categories.
    Instrument kind/form identity remains in the original request/result sidecar.
    """
    assessed_at = TimeInterval(start=assessed_at, end=assessed_at).end
    req = ModelCRequest.model_validate(request.model_dump())
    original = IsolationConfinementAssessment.model_validate(result.model_dump())
    for name in (
        "subject_id",
        "mission_id",
        "dataset_id",
        "run_id",
        "data_origin",
        "assessed_at",
        "reference_interval",
        "assessment_interval",
    ):
        if getattr(req, name) != getattr(original, name):
            raise ResearchAdapterError(
                "Model C original request/result identity mismatch"
            )
    lookup = {e.observation.observation_id: e for e in req.evidence}
    for indicator in original.indicators:
        if isinstance(indicator, NumericIndicatorAssessment):
            baseline_records = (
                *indicator.baseline.included,
                *(x.evidence for x in indicator.baseline.excluded),
            )
            if any(
                lookup.get(e.observation.observation_id) != e for e in baseline_records
            ):
                raise ResearchAdapterError("Model C reference lineage mismatch")
            for finding in indicator.findings:
                if (
                    lookup.get(finding.evidence.observation.observation_id)
                    != finding.evidence
                ):
                    raise ResearchAdapterError("Model C finding lineage mismatch")
    reasons = ["model_c_native_scores_not_hybrid_context"]
    if any(i.indicator == "fatigue_self_report" for i in original.indicators):
        reasons.append("categorical_fatigue_context_only")
    if original.assessed_at > assessed_at:
        return ContextAdaptation(
            original,
            None,
            False,
            tuple(reasons + ["context_unavailable_at_assessment"]),
            req,
        )
    if policy is None:
        return ContextAdaptation(
            original,
            None,
            False,
            tuple(reasons + ["explicit_sleep_temporal_policy_required"]),
            req,
        )
    if (
        policy.source.metric != "sleep_duration"
        or policy.source.unit != "h"
        or policy.scope.kind != "astronaut"
        or policy.scope.astronaut_id != req.subject_id
        or policy.scope.mission_id != req.mission_id
        or policy.event_window != req.assessment_interval
    ):
        return ContextAdaptation(
            original,
            None,
            False,
            tuple(reasons + ["sleep_policy_scope_metric_or_window_mismatch"]),
            req,
        )
    # H1 validates exact dataset/run/source/sensor/epoch, units, quality, event support
    # and prospective ingestion for each original observation, preserving exclusions.
    summary = analyze_temporal_evidence(
        req.evidence, policy=policy, assessed_at=assessed_at
    )
    return ContextAdaptation(original, summary, False, tuple(reasons), req)


def assess_hybrid(
    investigation: Investigation,
    temporal: TemporalSummary,
    *,
    policy: HybridPolicy,
    assessed_at: datetime,
    evidence: Sequence[ResearchEvidence],
    contexts: Sequence[ContextAdaptation] = (),
) -> AdaptedHybridAssessment:
    """H2 revalidates scope/source/availability; B/C remain separate sidecars.

    No model context can create a hypothesis or change the immutable M2 snapshot.
    Eligible A contexts are checked again by H2 against original evidence.
    """
    environmental = tuple(
        c.native_result
        for c in contexts
        if c.model_context_eligible
        and isinstance(c.native_result, EnvironmentalAnomalyContext)
    )
    assessment = evaluate_hybrid_evidence(
        investigation,
        temporal,
        policy=policy,
        assessed_at=assessed_at,
        m2_evidence=evidence,
        model_contexts=environmental,
    )
    return AdaptedHybridAssessment(assessment, tuple(contexts))
