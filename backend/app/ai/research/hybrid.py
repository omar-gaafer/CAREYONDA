"""AI-H2 deterministic research association, with immutable M2/AI-H1 snapshots."""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256

from app.ai.research.evidence_association import (
    check_finding,
    event_windows,
    index_evidence,
)
from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.baseline import ResearchEvidence, TimeInterval
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.hybrid import (
    EvidenceExclusion,
    HybridAssessment,
    HybridPolicy,
    ModelAssociationTrace,
    ResearchStatus,
    RuleAssessment,
    Verdict,
)
from app.schemas.investigation import Investigation
from app.schemas.temporal import TemporalSummary

LIMITATIONS = (
    "Research evidence association only; no medical truth, probability, confidence, severity or action is established.",
    "M2 toy expectations and caller-reviewed rules are descriptive assumptions, not causal or clinical rules.",
    "Statistical deviations are descriptive, not causal explanations or faithful model attribution.",
    "Temporal recovery describes return to a configured statistical band, not clinical recovery; measured trends do not establish health change.",
    "Exact-scope association only: subject/environment exposure and cross-scope links are not established.",
    "Availability, source identity and provenance are caller declarations, not independently authenticated.",
    "M2 ranking and safety policy are preserved and are not reevaluated by this assessment.",
)


class HybridInputError(ValueError):
    """Malformed identity or temporal evidence declaration; no sensitive values."""


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _verify_temporal(summary: TemporalSummary) -> None:
    original = (
        *summary.supporting_evidence,
        *(x.evidence for x in summary.excluded_evidence),
    )
    reproduced = analyze_temporal_evidence(
        original,
        policy=summary.policy,
        assessed_at=summary.assessed_at,
        model_contexts=tuple(c.context for c in summary.model_contexts),
    )
    if reproduced != summary:
        raise HybridInputError(
            "temporal summary differs from deterministic AI-H1 reconstruction"
        )


def _model_traces(
    contexts: Sequence[EnvironmentalAnomalyContext],
    temporal: TemporalSummary,
    policy: HybridPolicy,
    at: datetime,
) -> tuple[ModelAssociationTrace, ...]:
    if not contexts:
        return ()
    evidence = (
        *temporal.supporting_evidence,
        *(x.evidence for x in temporal.excluded_evidence),
    )
    # Reuse AI-H1's compatibility checks; no scoring or artifact loading occurs.
    checked = analyze_temporal_evidence(
        evidence,
        policy=temporal.policy,
        assessed_at=max(at, temporal.assessed_at),
        model_contexts=contexts,
    )
    identities = Counter((c.sample.sample_id, c.assessed_at) for c in contexts)
    results = []
    for item in checked.model_contexts:
        reasons = set(item.reason_codes)
        c = item.context
        if identities[(c.sample.sample_id, c.assessed_at)] > 1:
            reasons.add("conflicting_model_context_provenance")
        if temporal.policy.scope != policy.scope:
            reasons.add("model_scope_not_bound_to_m2")
        if c.assessed_at > at or c.sample.evidence_available_at > at:
            reasons.add("model_context_unavailable_at_assessment")
        eligible = not reasons
        reasons.add(
            "statistical_flag_not_hypothesis_evidence"
            if c.status == "flagged"
            else "not_flagged_does_not_establish_absence"
            if c.status == "not_flagged"
            else "model_finding_cannot_establish_claim"
        )
        results.append(
            ModelAssociationTrace(
                context_sha256=_digest(c.model_dump_json()),
                evidence_ids=tuple(
                    sorted(o.observation_id for o in c.sample.observations)
                ),
                eligible_context=eligible,
                outcome="cannot_establish",
                reason_codes=tuple(sorted(reasons)),
                explanation="Model context is descriptive statistical evidence only; no hazard-specific support, absence, causal mechanism or faithful feature attribution follows from its flag.",
            )
        )
    return tuple(results)


def evaluate_hybrid_evidence(
    investigation: Investigation,
    temporal: TemporalSummary,
    *,
    policy: HybridPolicy,
    assessed_at: datetime,
    m2_evidence: Sequence[ResearchEvidence],
    model_contexts: Sequence[EnvironmentalAnomalyContext] = (),
) -> HybridAssessment:
    """Assess one existing M2 hypothesis without creating rankings or modifying it.

    Original M2 observation snapshots are mandatory to resolve its scope-free IDs.
    Every expected metric needs an explicit matching rule. A pattern only qualifies
    independently verified M2 relations; model flags never provide their direction.
    Missing, incompatible and unavailable evidence cannot become positive support.
    """
    m2 = Investigation.model_validate(investigation.model_dump())
    t = TemporalSummary.model_validate(temporal.model_dump())
    p = HybridPolicy.model_validate(policy.model_dump())
    at = TimeInterval(start=assessed_at, end=assessed_at).end
    hypotheses = [h for h in m2.hypotheses if h.hypothesis_id == p.hypothesis_id]
    if len(hypotheses) != 1:
        raise HybridInputError("exactly one existing M2 hypothesis must match policy")
    if m2.reference_timestamp > event_windows(m2)[0].start:
        raise HybridInputError("M2 reference overlaps current event window")
    _verify_temporal(t)
    originals = tuple(
        ResearchEvidence.model_validate(e.model_dump()) for e in m2_evidence
    )
    all_temporal = (*t.supporting_evidence, *(e.evidence for e in t.excluded_evidence))
    index = index_evidence(originals, all_temporal)
    hypothesis = hypotheses[0]
    rules = {r.source.metric: r for r in p.rules}
    if not set(rules) <= set(hypothesis.expected_relations):
        raise HybridInputError(
            "policy metrics must belong to the existing M2 hypothesis"
        )
    findings = (
        *hypothesis.supporting_evidence,
        *hypothesis.contradictory_evidence,
        *hypothesis.missing_evidence,
    )
    steps: list[RuleAssessment] = []
    missing: set[str] = set()
    exclusions: list[EvidenceExclusion] = []
    current_window, _ = event_windows(m2)
    for metric, expected in sorted(hypothesis.expected_relations.items()):
        rule = rules.get(metric)
        candidates = [f for f in findings if f.metric == metric]
        finding = candidates[0] if len(candidates) == 1 else None
        current_ids = tuple(sorted(set(finding.observation_ids))) if finding else ()
        ref_ids = (
            tuple(sorted(set(finding.reference_observation_ids))) if finding else ()
        )
        reasons: set[str] = set()
        incompatible = False
        relation = None
        pattern = None
        if rule is None:
            reasons.add("missing_association_rule")
        elif rule.expected_relation != expected:
            reasons.add("policy_m2_expectation_mismatch")
            incompatible = True
        elif finding is None:
            reasons.add("missing_or_ambiguous_m2_finding")
            incompatible = len(candidates) > 1
        else:
            relation, codes, incompatible = check_finding(
                finding, rule, p, m2, index, at
            )
            reasons.update(codes)
        if len(set(m2.observation_ids)) != len(m2.observation_ids) or len(
            set(m2.reference_observation_ids)
        ) != len(m2.reference_observation_ids):
            reasons.add("duplicate_m2_evidence_reference")
            incompatible = True
        if m2.timestamp > at:
            reasons.add("m2_event_unavailable_at_assessment")
        if rule is not None and rule.required_temporal_patterns:
            pattern = t.pattern
            if (
                t.policy.scope != p.scope
                or t.policy.source != rule.source
                or t.policy.event_window != current_window
            ):
                reasons.add("temporal_scope_source_or_window_mismatch")
                incompatible = True
            if t.assessed_at > at:
                reasons.add("temporal_summary_unavailable_at_assessment")
            if t.abstention_reasons:
                reasons.update(t.abstention_reasons)
            if t.pattern not in rule.required_temporal_patterns:
                reasons.add("temporal_pattern_not_eligible")
            if not reasons and set(t.observation_ids) != set(current_ids):
                reasons.add("temporal_m2_lineage_mismatch")
                incompatible = True
            if (
                t.supporting_evidence
                and (
                    at - t.supporting_evidence[-1].observation.timestamp
                ).total_seconds()
                > rule.source.maximum_age_seconds
            ):
                reasons.add("stale_temporal_evidence")
        outcome: Verdict
        if reasons:
            outcome = "incompatible" if incompatible else "cannot_establish"
            missing.add(metric)
            exclusions.append(
                EvidenceExclusion(
                    evidence_ids=tuple(sorted(set(current_ids + ref_ids))),
                    reason_codes=tuple(sorted(reasons)),
                )
            )
        else:
            outcome = "supports" if relation == expected else "contradicts"
        steps.append(
            RuleAssessment(
                rule_id=rule.rule_id if rule else "unconfigured-association",
                metric=metric,
                claim=f"M2 {p.hypothesis_id} descriptive expectation: {metric} {expected}.",
                expected_relation=expected,
                observed_relation=relation,
                outcome=outcome,
                evidence_ids=current_ids,
                reference_evidence_ids=ref_ids,
                temporal_pattern=pattern,
                event_window=current_window,
                reason_codes=tuple(sorted(reasons)),
                explanation=(
                    "Resolved observations and the configured association rule support this descriptive metric expectation; they do not establish medical or causal truth."
                    if outcome == "supports"
                    else "Resolved observations contradict this descriptive metric expectation; they do not establish hazard absence."
                    if outcome == "contradicts"
                    else "The association checks cannot establish an eligible metric relationship; the recorded reasons identify missing, unavailable or excluded evidence."
                ),
            )
        )
    # Preserve original contexts; identical references shared by H1 and caller are
    # one sidecar, never independent votes. Conflicting sample identities quarantine.
    contexts_by_digest = {
        _digest(c.model_dump_json()): EnvironmentalAnomalyContext.model_validate(
            c.model_dump()
        )
        for c in (*model_contexts, *(x.context for x in t.model_contexts))
    }
    contexts = tuple(contexts_by_digest[k] for k in sorted(contexts_by_digest))
    model_steps = _model_traces(contexts, t, p, at)
    exclusions.extend(
        EvidenceExclusion(evidence_ids=s.evidence_ids, reason_codes=s.reason_codes)
        for s in model_steps
        if not s.eligible_context
    )
    if p.require_model_context and not any(s.eligible_context for s in model_steps):
        missing.add("required_compatible_model_context")
    referenced = {
        i for f in findings for i in (*f.observation_ids, *f.reference_observation_ids)
    }
    unassociated = set(index.records) - referenced
    if unassociated:
        exclusions.append(
            EvidenceExclusion(
                evidence_ids=tuple(sorted(unassociated)),
                reason_codes=("not_referenced_by_evaluated_m2_hypothesis",),
            )
        )
    supporting = tuple(
        sorted({i for s in steps if s.outcome == "supports" for i in s.evidence_ids})
    )
    contradicting = tuple(
        sorted({i for s in steps if s.outcome == "contradicts" for i in s.evidence_ids})
    )
    status: ResearchStatus
    if supporting and contradicting:
        status = "mixed_evidence"
    elif any(s.outcome == "incompatible" for s in steps):
        status = "incompatible_evidence"
    elif missing:
        status = "insufficient_evidence"
    elif supporting:
        status = "supported_by_available_evidence"
    elif contradicting:
        status = "contradicted_by_available_evidence"
    else:
        status = "insufficient_evidence"
        missing.add("no_directional_evidence")
    abstentions = (
        tuple(sorted({r for s in steps for r in s.reason_codes} | missing))
        if status in {"insufficient_evidence", "incompatible_evidence"}
        else ()
    )
    return HybridAssessment(
        schema_version="1.0.0",
        interpretation="research_only",
        method_version="hybrid-evidence-1.0.0",
        original_investigation=m2,
        original_m2_sha256=_digest(m2.model_dump_json()),
        hypothesis_id=p.hypothesis_id,
        policy=p,
        assessed_at=at,
        temporal_summary=t,
        evidence_snapshots=tuple(
            sorted(
                (*originals, *all_temporal),
                key=lambda e: (
                    e.observation.timestamp,
                    e.observation.observation_id,
                    e.model_dump_json(),
                ),
            )
        ),
        model_contexts=contexts,
        supporting_evidence_ids=supporting,
        contradicting_evidence_ids=contradicting,
        missing_evidence=tuple(sorted(missing)),
        unavailable_or_incompatible_evidence=tuple(exclusions),
        relevant_temporal_patterns=tuple(
            sorted(
                {s.temporal_pattern for s in steps if s.temporal_pattern is not None}
            )
        ),
        reasoning_steps=tuple(steps),
        model_reasoning_steps=model_steps,
        status=status,
        abstention_reasons=abstentions,
        limitations=(*LIMITATIONS, *t.quality_limitations),
    )
