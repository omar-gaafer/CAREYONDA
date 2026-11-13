"""Minimal reference-based hypothesis ranking. No probabilities or clinical rules."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from hashlib import sha256

from app.ai.explanations import explain_hypothesis
from app.features.temporal_features import FeatureSample, SampleAnchor, build_features
from app.quality.validator import evaluate_quality
from app.schemas.evidence import EvidenceFinding, EvidenceQualityIssue, EvidenceRelation
from app.schemas.investigation import (
    Compatibility,
    HypothesisId,
    HypothesisResult,
    Investigation,
    InvestigationStatus,
)
from app.schemas.observation import METRIC_REGISTRY, NumericMeasurement, Observation

# Expectations are toy pattern definitions, not clinical or causal rules.
_RULES: tuple[tuple[HypothesisId, tuple[tuple[str, EvidenceRelation], ...]], ...] = (
    (
        "baseline",
        (
            ("heart_rate", "within_reference"),
            ("cabin_co2_partial_pressure", "within_reference"),
            ("sleep_duration", "within_reference"),
            ("fatigue_self_report", "rested_reported"),
            ("exercise_active", "inactive"),
        ),
    ),
    (
        "elevated_co2",
        (
            ("cabin_co2_partial_pressure", "above_reference"),
            ("heart_rate", "above_reference"),
        ),
    ),
    (
        "sleep_deprivation",
        (
            ("sleep_duration", "below_reference"),
            ("fatigue_self_report", "fatigue_reported"),
        ),
    ),
    (
        "recent_exercise",
        (("exercise_active", "active"), ("heart_rate", "above_reference")),
    ),
)
_METRICS = (
    "heart_rate",
    "cabin_co2_partial_pressure",
    "sleep_duration",
    "fatigue_self_report",
    "exercise_active",
)
_COMMON_LIMITATIONS = (
    "Pattern rules are synthetic assumptions, not clinical validation or causal inference.",
    "Caller-selected reference is an empirical comparator, not a physiological normal range.",
    "No probability or clinical confidence is estimated; alternatives outside this catalogue remain possible.",
    "Event-time windows include late arrivals retrospectively; online availability is not established.",
    "Safety policies and procedures have not been evaluated; no action is recommended.",
)


class ReasoningInputError(ValueError):
    """Invalid reasoning context; messages contain no observation values."""


def _current_ids(sample: FeatureSample, metric: str) -> tuple[str, ...]:
    suffix = (
        "mean" if METRIC_REGISTRY[metric].measurement_kind == "numeric" else "latest"
    )
    return sample.evidence[f"{metric}_{suffix}"]


def _simultaneous_conflict(
    ids: tuple[str, ...], lookup: dict[str, Observation]
) -> bool:
    groups: dict[datetime, set[str]] = defaultdict(set)
    for oid in ids:
        observation = lookup[oid]
        groups[observation.timestamp].add(observation.measurement.model_dump_json())
    return any(len(values) > 1 for values in groups.values())


def _finding(
    metric: str,
    current: FeatureSample,
    reference: FeatureSample,
    lookup: dict[str, Observation],
) -> EvidenceFinding:
    definition = METRIC_REGISTRY[metric]
    unit = definition.canonical_unit or "1"
    numeric = definition.measurement_kind == "numeric"
    ids = _current_ids(current, metric)
    reference_ids = _current_ids(reference, metric) if numeric else ()
    current_window_ids = current.evidence[f"{metric}_missing"]
    value = current.values[f"{metric}_{'mean' if numeric else 'latest'}"]
    # For categorical/boolean metrics examine all valid window records for
    # simultaneous disagreement, not just M1.2's deterministic latest tie-break.
    current_valid_ids = tuple(
        oid
        for oid in current_window_ids
        if evaluate_quality(lookup[oid]).status == "valid"
    )
    if _simultaneous_conflict(current_valid_ids, lookup) or (
        numeric and _simultaneous_conflict(reference_ids, lookup)
    ):
        return EvidenceFinding(
            metric=metric,
            unit=unit,
            relation="conflicting",
            observation_ids=current_valid_ids,
            reference_observation_ids=reference_ids,
            explanation=f"{metric}: simultaneous usable readings disagree; no value was chosen as authoritative",
        )
    if not ids or (numeric and not reference_ids):
        return EvidenceFinding(
            metric=metric,
            unit=unit,
            relation="missing",
            observation_ids=current_window_ids,
            reference_observation_ids=reference.evidence[f"{metric}_missing"]
            if numeric
            else (),
            explanation=f"{metric}: no usable {'current' if not ids else 'reference'} evidence in the selected window",
        )
    assert value is not None
    if numeric:
        reference_values = []
        for oid in reference_ids:
            measurement = lookup[oid].measurement
            assert isinstance(measurement, NumericMeasurement)
            reference_values.append(measurement.value)
        lower, upper = min(reference_values), max(reference_values)
        relation: EvidenceRelation = (
            "above_reference"
            if value > upper
            else "below_reference"
            if value < lower
            else "within_reference"
        )
        return EvidenceFinding(
            metric=metric,
            unit=unit,
            relation=relation,
            observation_ids=ids,
            reference_observation_ids=reference_ids,
            observed_value=value,
            reference_minimum=lower,
            reference_maximum=upper,
            explanation=f"{metric}: window mean is {relation.replace('_', ' ')} (empirical comparator, not a clinical limit)",
        )
    relation = (
        ("active" if value == 1 else "inactive")
        if metric == "exercise_active"
        else ("fatigue_reported" if value > 0 else "rested_reported")
    )
    return EvidenceFinding(
        metric=metric,
        unit=unit,
        relation=relation,
        observation_ids=ids,
        observed_value=value,
        explanation=f"{metric}: latest usable report is {relation.replace('_', ' ')}",
    )


def _hypothesis(
    hypothesis: HypothesisId,
    expectations: tuple[tuple[str, EvidenceRelation], ...],
    findings: dict[str, EvidenceFinding],
) -> HypothesisResult:
    supporting: list[EvidenceFinding] = []
    contradictory: list[EvidenceFinding] = []
    missing: list[EvidenceFinding] = []
    uncertainty: list[str] = [
        "Compatibility is qualitative; no probability or causal certainty is estimated."
    ]
    for metric, expected in expectations:
        finding = findings[metric]
        if finding.relation == "missing":
            missing.append(finding)
            uncertainty.append(f"{metric}: missing evidence")
        elif finding.relation == "conflicting":
            contradictory.append(finding)
            uncertainty.append(f"{metric}: simultaneous conflicting evidence")
        elif finding.relation == expected:
            supporting.append(finding)
        else:
            contradictory.append(finding)
    compatibility: Compatibility
    if supporting and contradictory:
        compatibility = "mixed"
    elif contradictory:
        compatibility = "contradicted"
    elif missing:
        compatibility = "partial" if supporting else "insufficient"
    else:
        compatibility = "supported"
    if contradictory:
        uncertainty.append("Observed pattern contradicts one or more expectations.")
    return HypothesisResult(
        hypothesis_id=hypothesis,
        rank=1,
        compatibility=compatibility,
        expected_relations=dict(expectations),
        supporting_evidence=tuple(supporting),
        contradictory_evidence=tuple(contradictory),
        missing_evidence=tuple(missing),
        explanation=explain_hypothesis(
            hypothesis, compatibility, supporting, contradictory, missing
        ),
        uncertainty=tuple(uncertainty),
    )


def _rank_key(result: HypothesisResult) -> tuple[int, int, int, int]:
    if result.compatibility == "insufficient":
        return (4, 0, 0, 0)
    priority = ("supported", "partial", "mixed", "contradicted", "insufficient")
    return (
        priority.index(result.compatibility),
        len(result.contradictory_evidence),
        len(result.missing_evidence),
        -len(result.supporting_evidence),
    )


def investigate(
    observations: Sequence[Observation],
    anchor: SampleAnchor,
    reference_observations: Sequence[Observation],
    reference_anchor: SampleAnchor,
    window_seconds: int = 300,
) -> Investigation:
    """Compare causal feature windows with an explicitly supplied earlier reference.

    Reference origin/labels are never used to infer that it is a true baseline.
    The caller must select a suitable comparator; different contexts are allowed
    but never described as a personalized baseline. No reference is auto-mined.
    """
    if window_seconds <= 0:
        raise ReasoningInputError("window_seconds must be positive")
    if reference_anchor.timestamp > anchor.timestamp - timedelta(
        seconds=window_seconds
    ):
        raise ReasoningInputError("reference must end before the current window begins")
    # Each source collection may include other scopes/times, as in M1.2. Shared
    # IDs across collections must refer to the exact same validated observation.
    lookup: dict[str, Observation] = {}
    for observation in (*observations, *reference_observations):
        existing = lookup.get(observation.observation_id)
        if existing is not None and existing != observation:
            raise ReasoningInputError("conflicting records reuse an observation ID")
        lookup[observation.observation_id] = observation
    current = build_features(observations, [anchor], window_seconds)[0]
    reference = build_features(
        reference_observations, [reference_anchor], window_seconds
    )[0]
    findings = {
        metric: _finding(metric, current, reference, lookup) for metric in _METRICS
    }
    results = [_hypothesis(name, rules, findings) for name, rules in _RULES]
    results.sort(key=lambda result: (*_rank_key(result), result.hypothesis_id))
    ranked: list[HypothesisResult] = []
    previous: tuple[int, int, int, int] | None = None
    rank = 1
    for index, result in enumerate(results, start=1):
        key = _rank_key(result)
        if key != previous:
            rank = index
        ranked.append(result.model_copy(update={"rank": rank}))
        previous = key
    supported = [result for result in ranked if result.compatibility == "supported"]
    status: InvestigationStatus
    selected: HypothesisId | None = None
    if any(f.relation == "conflicting" for f in findings.values()):
        status = "conflicting_evidence"
    elif len(supported) > 1:
        status = "ambiguous"
    elif len(supported) == 1:
        status = "ranked"
        selected = supported[0].hypothesis_id
    else:
        status = "insufficient_evidence"
    quality_issues: list[EvidenceQualityIssue] = []
    for window, sample in (("current", current), ("reference", reference)):
        for oid in sample.window_observation_ids:
            quality = evaluate_quality(lookup[oid])
            if quality.status != "valid":
                quality_issues.append(
                    EvidenceQualityIssue.model_validate(
                        {
                            "window": window,
                            "observation_id": oid,
                            "metric": lookup[oid].metric,
                            "status": quality.status,
                            "reason_codes": quality.reason_codes,
                        }
                    )
                )
    limitations = list(_COMMON_LIMITATIONS)
    if quality_issues:
        limitations.append(
            "Non-valid observations were excluded from numerical/state evidence; coverage is incomplete."
        )
    if status != "ranked":
        limitations.append(
            "No unique fully supported hypothesis; abstaining from selection."
        )
    if any(f.relation == "missing" for f in findings.values()):
        limitations.append(
            "One or more observation/reference metrics are missing or unusable."
        )
    identity = (
        f"reference-rules-1.0.0:{anchor.model_dump_json()}:"
        f"{reference_anchor.model_dump_json()}:{window_seconds}:"
        f"{current.window_observation_ids}:{reference.window_observation_ids}"
    )
    return Investigation(
        investigation_id="investigation-" + sha256(identity.encode()).hexdigest()[:32],
        sample_id=anchor.sample_id,
        timestamp=anchor.timestamp,
        reference_sample_id=reference_anchor.sample_id,
        reference_timestamp=reference_anchor.timestamp,
        window_seconds=window_seconds,
        status=status,
        selected_hypothesis=selected,
        hypotheses=tuple(ranked),
        observation_ids=current.window_observation_ids,
        reference_observation_ids=reference.window_observation_ids,
        uncertainty=tuple(limitations),
        quality_issues=tuple(quality_issues),
    )
