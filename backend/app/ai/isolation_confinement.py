"""Model C: deterministic per-subject longitudinal comparison (research only).

For ``sleep_duration`` the subject's own reference period is binned (bin width is
a research parameter), each occupied bin is summarised by its median, and the
reference is the median of bin medians with the raw (unscaled) median absolute
deviation of those bin medians. Every reading in the later assessment period is
then described with the M4.2 ``absolute_deviation_over_raw_mad`` definition.
Bin medians give each period equal weight regardless of how often it was sampled.

For ``fatigue_self_report`` (categorical) valid reports are counted per registry
category in both periods. No score, distance or threshold is computed.

Nothing here diagnoses, labels a condition, combines indicators, infers a cause or
recommends an action. Missing, invalid, unavailable or mismatched records are kept
as explicit exclusions or abstentions. Pure functions: no I/O, clock or randomness.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from hashlib import sha256
from math import ceil
from statistics import median
from typing import Literal

from pydantic import ValidationError

from app.schemas.anomaly import AnomalyFinding, AnomalyPolicy
from app.schemas.baseline import (
    BaselinePolicy,
    BaselineProfile,
    ExcludedEvidence,
    ReferenceBin,
    ReferenceSummary,
    ResearchEvidence,
    SourceScope,
    TimeInterval,
)
from app.schemas.isolation_confinement import (
    MODEL_C_ID,
    MODEL_C_VERSION,
    REGISTRY_REPORTING_MODE,
    SUPPORTED_INDICATORS,
    CategoricalIndicatorAssessment,
    CategoryCount,
    FindingSummary,
    IndicatorSource,
    IsolationConfinementAssessment,
    ModelCParameters,
    ModelCRequest,
    NumericIndicatorAssessment,
    ProvenanceNature,
)
from app.schemas.observation import (
    METRIC_REGISTRY,
    CategoricalMeasurement,
    NumericMeasurement,
)

METHOD_VERSION = "model-c-bin-median-raw-mad-1.0.0"
NUMERIC_UNIT = "h"

# Literal sets mirroring the M4.2 and Model C contracts, for typed locals.
ProfileStatus = Literal[
    "ready", "unsupported", "insufficient_reference", "flat_reference"
]
ScoreStatus = Literal[
    "scored",
    "flat_reference",
    "insufficient_reference",
    "unsupported",
    "invalid_observation",
]
Direction = Literal["above", "below", "equal", "unassessed"]
ThresholdStatus = Literal["unassessed", "exceeded", "not_exceeded"]
IndicatorStatus = Literal["assessed", "abstained"]
OverallStatus = Literal["assessed", "partially_assessed", "abstained"]

# Unvalidated research defaults chosen for daily behavioural records. They are
# not clinical, NASA-approved or operational limits; callers may override them.
DEFAULT_RESEARCH_PARAMETERS = ModelCParameters(
    parameter_status="unvalidated_research_default",
    bin_duration_seconds=86_400.0,
    minimum_occupied_bins=7,
    minimum_observed_span_seconds=6 * 86_400.0,
    minimum_occupancy_fraction=0.5,
    maximum_gap_seconds=3 * 86_400.0,
    # Measured from reference end to assessment time (M4.2), so it must cover
    # the whole assessment period; 7 days allows up to a weekly period.
    maximum_reference_age_seconds=7 * 86_400.0,
    minimum_reference_reports=7,
    availability_mode="retrospective",
)

_NATURE: dict[str, ProvenanceNature] = {
    "measured": "direct_measurement",
    "self_reported": "self_report",
    "derived": "derived",
    "simulated": "simulated",
}
_NATURE_ORDER: tuple[ProvenanceNature, ...] = (
    "direct_measurement",
    "self_report",
    "derived",
    "simulated",
)


class ModelCInputError(ValueError):
    """The request cannot be assessed as declared. Messages never echo values."""


def _digest(*parts: object) -> str:
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(text.encode()).hexdigest()[:32]


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _fmt(value: float) -> str:
    return f"{value:.4g}"


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _provenance(items: Iterable[ResearchEvidence]) -> tuple[ProvenanceNature, ...]:
    seen = {_NATURE[e.observation.provenance.origin] for e in items}
    return tuple(n for n in _NATURE_ORDER if n in seen)


def _in_period(e: ResearchEvidence, period: TimeInterval) -> bool:
    return period.start < e.observation.timestamp <= period.end


def _support_fits(e: ResearchEvidence, period: TimeInterval) -> bool:
    return period.start < e.temporal_support.start and e.temporal_support.end <= (
        period.end
    )


def _quality_reason(e: ResearchEvidence) -> str | None:
    status = e.observation.quality.status
    return None if status == "valid" else f"quality_{status}"


def _instrument_note(source: IndicatorSource) -> str:
    if source.instrument_kind == "self_report_form":
        return (
            f" Instrument: self-report form {source.sensor_id} version "
            f"{source.sensor_epoch}; no physical sensor is involved, and exact "
            "matching applies to that form version."
        )
    if source.sensor_id is None:
        return " Instrument: sensor with undeclared identity."
    return (
        f" Instrument: sensor {source.sensor_id} epoch {source.sensor_epoch} "
        "(caller declaration, not independently verified)."
    )


def _source_matches(e: ResearchEvidence, source: IndicatorSource) -> bool:
    return (
        e.observation.provenance.source_id == source.source_id
        and e.sensor_id == source.sensor_id
        and e.sensor_epoch == source.sensor_epoch
    )


# --------------------------------------------------------------------------- numeric


def _baseline_policy(request: ModelCRequest, source: IndicatorSource) -> BaselinePolicy:
    p = request.parameters
    try:
        return BaselinePolicy(
            schema_version="1.0.0",
            interpretation="research_only",
            policy_id=f"model-c-{source.indicator}-reference",
            policy_version=MODEL_C_VERSION,
            source_scope=SourceScope(
                dataset_id=request.dataset_id,
                run_id=request.run_id,
                mission_id=request.mission_id,
                subject_id=request.subject_id,
                source_id=source.source_id,
                sensor_id=source.sensor_id,
                sensor_epoch=source.sensor_epoch,
                data_origin=request.data_origin,
            ),
            metric=source.indicator,
            unit=NUMERIC_UNIT,
            reference_interval=request.reference_interval,
            bin_duration_seconds=p.bin_duration_seconds,
            minimum_occupied_bins=p.minimum_occupied_bins,
            minimum_observed_span_seconds=p.minimum_observed_span_seconds,
            minimum_occupancy_fraction=p.minimum_occupancy_fraction,
            maximum_gap_seconds=p.maximum_gap_seconds,
            maximum_reference_age_seconds=p.maximum_reference_age_seconds,
            source_sensor_compatibility="exact_identity"
            if source.sensor_id is not None
            else "unavailable",
            availability_mode=p.availability_mode,
        )
    except ValidationError:
        raise ModelCInputError(
            "reference interval cannot satisfy the declared research parameters"
        ) from None


def _default_anomaly_policy() -> AnomalyPolicy:
    return AnomalyPolicy(
        schema_version="1.0.0",
        interpretation="research_only",
        policy_id="model-c-sleep_duration-deviation",
        policy_version=MODEL_C_VERSION,
        metric="sleep_duration",
        unit=NUMERIC_UNIT,
        score_definition="absolute_deviation_over_raw_mad",
        threshold_governance="unassessed",
        governance_source=f"Model C {MODEL_C_VERSION} default: no approved research threshold",
        calibration=None,
        threshold=None,
    )


def _partition_reference(
    candidates: Sequence[ResearchEvidence],
    policy: BaselinePolicy,
    assessed_at: datetime,
) -> tuple[list[ResearchEvidence], list[ExcludedEvidence]]:
    included: list[ResearchEvidence] = []
    excluded: list[ExcludedEvidence] = []
    for e in candidates:
        reasons: list[str] = []
        quality = _quality_reason(e)
        if quality is not None:
            reasons.append(quality)
        if not isinstance(e.observation.measurement, NumericMeasurement):
            reasons.append("measurement_unavailable")
        elif not e.matches(policy.source_scope, policy.metric, policy.unit):
            reasons.append("source_or_sensor_mismatch")
        if not _support_fits(e, policy.reference_interval):
            reasons.append("support_outside_reference")
        if not e.available_at(assessed_at, policy.availability_mode):
            reasons.append("unavailable_at_assessment")
        if reasons:
            excluded.append(ExcludedEvidence(evidence=e, reason_codes=tuple(reasons)))
        else:
            included.append(e)
    by_time: dict[datetime, set[str]] = {}
    for e in included:
        by_time.setdefault(e.observation.timestamp, set()).add(
            e.observation.measurement.model_dump_json()
        )
    conflicted = {t for t, values in by_time.items() if len(values) > 1}
    kept = [e for e in included if e.observation.timestamp not in conflicted]
    excluded += [
        ExcludedEvidence(
            evidence=e, reason_codes=("conflicting_simultaneous_readings",)
        )
        for e in included
        if e.observation.timestamp in conflicted
    ]
    return kept, excluded


def _value(e: ResearchEvidence) -> float:
    measurement = e.observation.measurement
    assert isinstance(measurement, NumericMeasurement)
    return measurement.value


def _baseline(
    request: ModelCRequest,
    source: IndicatorSource,
    candidates: Sequence[ResearchEvidence],
) -> BaselineProfile:
    policy = _baseline_policy(request, source)
    interval = policy.reference_interval
    included, excluded = _partition_reference(candidates, policy, request.assessed_at)
    duration = (interval.end - interval.start).total_seconds()
    width = policy.bin_duration_seconds
    total_bins = ceil(duration / width)
    members: dict[int, list[ResearchEvidence]] = {}
    for e in included:
        offset = (e.observation.timestamp - interval.start).total_seconds()
        members.setdefault(max(ceil(offset / width) - 1, 0), []).append(e)
    bins = tuple(
        ReferenceBin(
            index=index,
            observation_ids=tuple(e.observation.observation_id for e in members[index]),
        )
        for index in sorted(members)
    )
    times = sorted(e.observation.timestamp for e in included)
    span = (times[-1] - times[0]).total_seconds() if times else 0.0
    largest_gap = max(
        ((b - a).total_seconds() for a, b in zip(times, times[1:], strict=False)),
        default=0.0,
    )
    summary = ReferenceSummary(
        total_bins=total_bins,
        occupied_bins=len(bins),
        sample_count=len(included),
        occupancy_fraction=len(bins) / total_bins,
        observed_span_seconds=span,
        maximum_gap_seconds=largest_gap,
        bins=bins,
    )
    age = (request.assessed_at - interval.end).total_seconds()
    reasons: list[str] = []
    status: ProfileStatus
    if policy.source_sensor_compatibility != "exact_identity":
        status = "unsupported"
        reasons.append("sensor_identity_unavailable")
    else:
        if not included:
            reasons.append("no_valid_reference_evidence")
        if summary.occupied_bins < policy.minimum_occupied_bins:
            reasons.append("insufficient_occupied_bins")
        if span < policy.minimum_observed_span_seconds:
            reasons.append("insufficient_observed_span")
        if summary.occupancy_fraction < policy.minimum_occupancy_fraction:
            reasons.append("insufficient_occupancy_fraction")
        if largest_gap > policy.maximum_gap_seconds:
            reasons.append("reference_gap_exceeds_maximum")
        if age > policy.maximum_reference_age_seconds:
            reasons.append("reference_too_old")
        status = "insufficient_reference" if reasons else "ready"
    median_value: float | None = None
    raw_mad: float | None = None
    if status == "ready":
        bin_medians = [median(_value(e) for e in members[i]) for i in sorted(members)]
        median_value = float(median(bin_medians))
        raw_mad = float(median(abs(v - median_value) for v in bin_medians))
        if raw_mad == 0:
            status = "flat_reference"
            reasons.append("zero_reference_dispersion")
    ids = sorted(e.observation.observation_id for e in included)
    return BaselineProfile(
        schema_version="1.0.0",
        interpretation="research_only",
        profile_id="model-c-profile-"
        + _digest(policy.model_dump(mode="json"), ids, request.assessed_at),
        policy=policy,
        assessed_at=request.assessed_at,
        included=tuple(included),
        excluded=tuple(excluded),
        summary=summary,
        median_value=median_value,
        raw_mad=raw_mad,
        status=status,
        abstention_reasons=tuple(reasons),
        method_version=METHOD_VERSION,
    )


def _target_compatible(
    e: ResearchEvidence, baseline: BaselineProfile, assessed_at: datetime
) -> bool:
    policy = baseline.policy
    return (
        policy.source_sensor_compatibility == "exact_identity"
        and e.matches(policy.source_scope, policy.metric, policy.unit)
        and e.available_at(assessed_at, policy.availability_mode)
        and (assessed_at - policy.reference_interval.end).total_seconds()
        <= policy.maximum_reference_age_seconds
    )


def _finding(
    e: ResearchEvidence,
    baseline: BaselineProfile,
    policy: AnomalyPolicy,
    assessed_at: datetime,
) -> AnomalyFinding:
    obs = e.observation
    value = (
        obs.measurement.value
        if isinstance(obs.measurement, NumericMeasurement)
        else None
    )
    quality = obs.quality
    limitations = quality.reason_codes if quality.status != "valid" else ()
    signed: float | None = None
    score: float | None = None
    reasons: tuple[str, ...] = ()
    status: ScoreStatus
    if not _target_compatible(e, baseline, assessed_at):
        status = "unsupported"
        if value is None:
            reasons = ("target_measurement_unavailable",)
        elif baseline.policy.source_sensor_compatibility != "exact_identity":
            reasons = ("sensor_identity_unavailable",)
        else:
            reasons = ("target_incompatible_or_unavailable",)
    elif quality.status != "valid":
        status = "invalid_observation"
        reasons = (f"target_quality_{quality.status}",)
    elif baseline.status == "insufficient_reference":
        status = "insufficient_reference"
        reasons = ("baseline_insufficient_reference",)
    elif baseline.status == "unsupported":
        status = "unsupported"
        reasons = ("baseline_unsupported",)
    else:
        assert value is not None and baseline.median_value is not None
        signed = value - baseline.median_value
        if baseline.status == "flat_reference":
            status = "flat_reference"
            reasons = ("zero_reference_dispersion",)
        else:
            assert baseline.raw_mad is not None
            status = "scored"
            score = abs(signed) / baseline.raw_mad
    direction: Direction = (
        "unassessed"
        if signed is None
        else "above"
        if signed > 0
        else "below"
        if signed < 0
        else "equal"
    )
    threshold = policy.threshold
    threshold_status: ThresholdStatus = "unassessed"
    if threshold is not None and score is not None:
        exceeds = (
            score > threshold.value
            if threshold.comparison == "greater_than"
            else score >= threshold.value
        )
        threshold_status = "exceeded" if exceeds else "not_exceeded"
    if score is not None and signed is not None:
        explanation = (
            f"{obs.metric} {_fmt(value or 0.0)} h is {_fmt(abs(signed))} h {direction} "
            f"the personal reference median {_fmt(baseline.median_value or 0.0)} h; "
            f"raw-MAD score {_fmt(score)} (dimensionless; not a z-score, probability "
            f"or severity). Threshold: {threshold_status}."
        )
    else:
        explanation = (
            f"{obs.metric} reading not scored: {', '.join(reasons)}. "
            "No deviation score is reported for this reading."
        )
    return AnomalyFinding(
        schema_version="1.0.0",
        interpretation="research_only",
        finding_id="model-c-finding-"
        + _digest(baseline.profile_id, obs.observation_id, assessed_at),
        policy=policy,
        baseline=baseline,
        evidence=e,
        assessed_at=assessed_at,
        original_value=value,
        signed_deviation=signed,
        absolute_deviation=None if signed is None else abs(signed),
        raw_mad_score=score,
        direction=direction,
        score_status=status,
        threshold_status=threshold_status,
        evidence_ids=(obs.observation_id,),
        profile_lineage_ids=(baseline.profile_id,),
        quality_limitations=limitations,
        explanation=explanation,
        abstention_reasons=reasons,
        method_version=METHOD_VERSION,
    )


def _summary(findings: Sequence[AnomalyFinding]) -> FindingSummary:
    scored = [f for f in findings if f.score_status == "scored"]
    scores = [f.raw_mad_score for f in scored if f.raw_mad_score is not None]
    return FindingSummary(
        findings=len(findings),
        scored=len(scored),
        above_reference=sum(f.direction == "above" for f in scored),
        below_reference=sum(f.direction == "below" for f in scored),
        equal_to_reference=sum(f.direction == "equal" for f in scored),
        abstained=len(findings) - len(scored),
        median_raw_mad_score=float(median(scores)) if scores else None,
        maximum_raw_mad_score=max(scores) if scores else None,
        threshold_exceeded=sum(f.threshold_status == "exceeded" for f in scored),
    )


def _numeric_assessment(
    request: ModelCRequest,
    source: IndicatorSource,
    reference: Sequence[ResearchEvidence],
    targets: Sequence[ResearchEvidence],
) -> NumericIndicatorAssessment:
    baseline = _baseline(request, source, reference)
    policy = request.anomaly_policy or _default_anomaly_policy()
    findings = tuple(
        _finding(e, baseline, policy, request.assessed_at) for e in targets
    )
    summary = _summary(findings)
    reasons = list(baseline.abstention_reasons)
    if baseline.status == "ready" and summary.scored == 0:
        reasons.append("no_scored_assessment_readings")
    status: IndicatorStatus = (
        "assessed" if baseline.status == "ready" and summary.scored else "abstained"
    )
    if status == "abstained" and not reasons:
        reasons.append("no_scored_assessment_readings")
    ref, window = request.reference_interval, request.assessment_interval
    s = baseline.summary
    reference_text = (
        f"Personal reference {_stamp(ref.start)} to {_stamp(ref.end)}: {baseline.status}, "
        f"{s.occupied_bins}/{s.total_bins} bins occupied by {s.sample_count} valid "
        "readings"
        + (
            f", median of bin medians {_fmt(baseline.median_value)} h, raw MAD "
            f"{_fmt(baseline.raw_mad or 0.0)} h"
            if baseline.median_value is not None
            else ""
        )
        + "."
    )
    window_text = (
        f" Assessment period {_stamp(window.start)} to {_stamp(window.end)}: "
        f"{summary.scored} of {summary.findings} readings scored "
        f"({summary.above_reference} above, {summary.below_reference} below, "
        f"{summary.equal_to_reference} equal)"
        + (
            f", median raw-MAD score {_fmt(summary.median_raw_mad_score)}"
            if summary.median_raw_mad_score is not None
            else ""
        )
        + f"; threshold decisions: {summary.threshold_exceeded} exceeded."
    )
    abstain_text = f" Abstained: {', '.join(_unique(reasons))}." if reasons else ""
    return NumericIndicatorAssessment(
        kind="numeric_personal_baseline",
        indicator="sleep_duration",
        unit="h",
        registry_reporting_mode=REGISTRY_REPORTING_MODE["sleep_duration"],
        instrument_kind=source.instrument_kind,
        evidence_provenance=_provenance((*reference, *targets)),
        status=status,
        baseline=baseline,
        findings=findings,
        summary=summary,
        explanation=reference_text
        + window_text
        + abstain_text
        + _instrument_note(source),
        abstention_reasons=_unique(reasons),
    )


# ----------------------------------------------------------------------- categorical


def _categorical_assessment(
    request: ModelCRequest,
    source: IndicatorSource,
    reference: Sequence[ResearchEvidence],
    targets: Sequence[ResearchEvidence],
) -> CategoricalIndicatorAssessment:
    categories = METRIC_REGISTRY[source.indicator].categories
    mode = request.parameters.availability_mode
    excluded: list[ExcludedEvidence] = []

    def usable(e: ResearchEvidence, period: TimeInterval) -> bool:
        reasons: list[str] = []
        quality = _quality_reason(e)
        if quality is not None:
            reasons.append(quality)
        if not isinstance(e.observation.measurement, CategoricalMeasurement):
            reasons.append("measurement_unavailable")
        if not _source_matches(e, source):
            reasons.append("source_or_sensor_mismatch")
        if not _support_fits(e, period):
            reasons.append("support_outside_period")
        if not e.available_at(request.assessed_at, mode):
            reasons.append("unavailable_at_assessment")
        if reasons:
            excluded.append(ExcludedEvidence(evidence=e, reason_codes=tuple(reasons)))
        return not reasons

    ref_reports = [e for e in reference if usable(e, request.reference_interval)]
    window_reports = [e for e in targets if usable(e, request.assessment_interval)]

    def count(items: Sequence[ResearchEvidence], category: str) -> int:
        return sum(
            isinstance(e.observation.measurement, CategoricalMeasurement)
            and e.observation.measurement.value == category
            for e in items
        )

    counts = tuple(
        CategoryCount(
            category=c,
            reference_count=count(ref_reports, c),
            assessment_count=count(window_reports, c),
        )
        for c in categories
    )
    reasons: list[str] = []
    if len(ref_reports) < request.parameters.minimum_reference_reports:
        reasons.append("insufficient_reference_reports")
    if not window_reports:
        reasons.append("no_valid_assessment_reports")
    age = (request.assessed_at - request.reference_interval.end).total_seconds()
    if age > request.parameters.maximum_reference_age_seconds:
        reasons.append("reference_too_old")
    describe = ", ".join
    explanation = (
        f"Reference period: {describe(f'{c.category} {c.reference_count}' for c in counts)}"
        f" ({len(ref_reports)} valid reports). Assessment period: "
        f"{describe(f'{c.category} {c.assessment_count}' for c in counts)} "
        f"({len(window_reports)} valid reports). Counts are descriptive self-reports; "
        "no score, distance or threshold is applied."
        + (f" Abstained: {', '.join(reasons)}." if reasons else "")
    )
    return CategoricalIndicatorAssessment(
        kind="categorical_report_distribution",
        indicator="fatigue_self_report",
        registry_reporting_mode=REGISTRY_REPORTING_MODE["fatigue_self_report"],
        instrument_kind=source.instrument_kind,
        evidence_provenance=_provenance((*reference, *targets)),
        status="abstained" if reasons else "assessed",
        categories=counts,
        reference_report_ids=tuple(e.observation.observation_id for e in ref_reports),
        assessment_report_ids=tuple(
            e.observation.observation_id for e in window_reports
        ),
        excluded=tuple(excluded),
        explanation=explanation + _instrument_note(source),
        abstention_reasons=tuple(reasons),
    )


# ------------------------------------------------------------------------ entry point


def assess_isolation_confinement(
    request: ModelCRequest,
) -> IsolationConfinementAssessment:
    """Assess each declared indicator separately for one subject (deterministic)."""
    ordered = sorted(
        request.evidence,
        key=lambda e: (e.observation.timestamp, e.observation.observation_id),
    )
    used: set[str] = set()
    results: list[NumericIndicatorAssessment | CategoricalIndicatorAssessment] = []
    by_indicator: dict[str, IndicatorSource] = {s.indicator: s for s in request.sources}
    for indicator in SUPPORTED_INDICATORS:
        source = by_indicator.get(indicator)
        if source is None:
            continue
        items = [e for e in ordered if e.observation.metric == indicator]
        reference = [e for e in items if _in_period(e, request.reference_interval)]
        targets = [e for e in items if _in_period(e, request.assessment_interval)]
        used.update(e.observation.observation_id for e in (*reference, *targets))
        if indicator == "sleep_duration":
            results.append(_numeric_assessment(request, source, reference, targets))
        else:
            results.append(_categorical_assessment(request, source, reference, targets))
    assessed = sum(r.status == "assessed" for r in results)
    status: OverallStatus = (
        "assessed"
        if assessed == len(results)
        else "abstained"
        if assessed == 0
        else "partially_assessed"
    )
    return IsolationConfinementAssessment(
        schema_version="1.0.0",
        interpretation="research_only",
        model_id=MODEL_C_ID,
        model_version=MODEL_C_VERSION,
        method_version=METHOD_VERSION,
        assessment_id="model-c-assessment-" + _digest(request.model_dump(mode="json")),
        subject_id=request.subject_id,
        mission_id=request.mission_id,
        dataset_id=request.dataset_id,
        run_id=request.run_id,
        data_origin=request.data_origin,
        assessed_at=request.assessed_at,
        reference_interval=request.reference_interval,
        assessment_interval=request.assessment_interval,
        parameters=request.parameters,
        indicators=tuple(results),
        status=status,
        abstention_reasons=("no_indicator_assessed",) if status == "abstained" else (),
        unused_evidence_ids=tuple(
            e.observation.observation_id
            for e in ordered
            if e.observation.observation_id not in used
        ),
    )
