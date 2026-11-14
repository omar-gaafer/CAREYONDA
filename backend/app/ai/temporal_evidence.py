"""Deterministic, offline AI-H1 temporal descriptions; no clinical inference."""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from math import isfinite

from app.schemas.baseline import ExcludedEvidence, ResearchEvidence, TimeInterval
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.observation import NumericMeasurement
from app.schemas.temporal import (
    ModelContextEvidence,
    Pattern,
    TemporalPolicy,
    TemporalSummary,
)


class TemporalInputError(ValueError):
    """Ambiguous identities or invalid temporal analysis input."""


def _exclusion(e: ResearchEvidence, p: TemporalPolicy, at: datetime) -> str | None:
    obs = e.observation
    # Availability is tested before values/quality; future values never influence patterns.
    if not e.available_at(at, "prospective"):
        return "unavailable_at_assessment"
    if (
        not p.event_window.start
        < e.temporal_support.start
        <= (e.temporal_support.end)
        <= p.event_window.end
    ):
        return "outside_window"
    if not p.source.matches(e) or obs.scope != p.scope:
        return "scope_or_source_mismatch"
    if obs.quality.status != "valid":
        return "quality_" + obs.quality.status
    if not isinstance(obs.measurement, NumericMeasurement):
        return "non_numeric"
    if obs.measurement.unit != p.source.unit:
        return "unit_mismatch"
    return None


def _describe(
    values: list[float], times: list[datetime], p: TemporalPolicy
) -> tuple[Pattern, float | None]:
    flags = [v < p.reference_lower or v > p.reference_upper for v in values]
    run = longest = 0
    for flag in flags:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    # Recovery requires a sustained anomalous prefix followed by a sustained return.
    first_clear = next((i for i, flag in enumerate(flags) if not flag), len(flags))
    if (
        first_clear >= p.minimum_run
        and len(flags) - first_clear >= p.minimum_run
        and not any(flags[first_clear:])
    ):
        return "recovery", None
    if longest >= p.minimum_run:
        return "persistent_anomaly", None
    if sum(flags) == 1 and not flags[0] and not flags[-1]:
        return "isolated_spike", None
    # Monotonic measured trend; slope is endpoint change per elapsed event second.
    slope = (values[-1] - values[0]) / (times[-1] - times[0]).total_seconds()
    if not isfinite(slope):
        return "abstained", None
    deltas = [b - a for a, b in zip(values, values[1:], strict=False)]
    monotonic = all(d >= 0 for d in deltas) or all(d <= 0 for d in deltas)
    if monotonic and abs(slope) >= p.minimum_slope_per_second:
        worsening = (slope > 0) == (p.trend_direction == "higher_is_worsening")
        return ("worsening" if worsening else "improving"), slope
    return "no_pattern", slope


def _contexts(
    contexts: Sequence[EnvironmentalAnomalyContext],
    p: TemporalPolicy,
    at: datetime,
    included: Sequence[ResearchEvidence],
) -> tuple[ModelContextEvidence, ...]:
    results: list[ModelContextEvidence] = []
    lookup = {e.observation.observation_id: e.observation for e in included}
    for original in contexts:
        c = EnvironmentalAnomalyContext.model_validate(original.model_dump())
        sample = c.sample
        reasons: list[str] = []
        if c.assessed_at > at or sample.evidence_available_at > at:
            reasons.append("model_context_unavailable_at_assessment")
        if sample.assessment_mode != "live":
            reasons.append("historical_replay_not_prospective")
        if (
            p.scope.kind != "spacecraft"
            or sample.scope.mission_id != p.scope.mission_id
            or sample.scope.spacecraft_id != p.scope.spacecraft_id
            or sample.scope.dataset_id != p.source.dataset_id
            or sample.scope.run_id != p.source.run_id
            or sample.scope.data_origin != p.source.data_origin
        ):
            reasons.append("model_context_scope_mismatch")
        if not p.event_window.start < sample.event_time_utc <= p.event_window.end:
            reasons.append("model_context_outside_window")
        if (at - sample.event_time_utc).total_seconds() > p.source.maximum_age_seconds:
            reasons.append("model_context_stale")
        # Require exact snapshots, not merely caller-reused IDs. Multimetric sidecars
        # may contain additional metrics but cannot introduce unvalidated lineage.
        target = [o for o in sample.observations if o.metric == p.source.metric]
        if not target or any(lookup.get(o.observation_id) != o for o in target):
            reasons.append("model_context_lineage_unavailable")
        if (
            c.availability != "available"
            or c.compatibility != "compatible"
            or c.status in {"abstained", "unassessed"}
        ):
            reasons.append("model_finding_unavailable_or_abstained")
        results.append(
            ModelContextEvidence(
                context=c, used=not reasons, reason_codes=tuple(sorted(reasons))
            )
        )
    return tuple(
        sorted(
            results,
            key=lambda r: (
                r.context.sample.event_time_utc,
                r.context.sample.sample_id,
                r.context.assessed_at,
                r.context.model_dump_json(),
            ),
        )
    )


def analyze_temporal_evidence(
    evidence: Sequence[ResearchEvidence],
    *,
    policy: TemporalPolicy,
    assessed_at: datetime,
    model_contexts: Sequence[EnvironmentalAnomalyContext] = (),
) -> TemporalSummary:
    """Analyze one exact numeric source/scope in a bounded prospective window.

    Revalidate boundary inputs, sort by event time, reject duplicate observation
    identities, and abstain across missing/invalid readings, gaps or staleness.
    Optional Model A sidecars are contextual provenance only; they never affect
    numeric pattern classification. No interpolation, fitting or I/O occurs.
    """
    p = TemporalPolicy.model_validate(policy.model_dump())
    # Reuse the existing timestamp contract rather than accepting naive datetimes.
    at = TimeInterval(start=assessed_at, end=assessed_at).end
    if at < p.event_window.end:
        raise TemporalInputError("assessment precedes event window end")
    items = [ResearchEvidence.model_validate(e.model_dump()) for e in evidence]
    ids = [e.observation.observation_id for e in items]
    if len(set(ids)) != len(ids):
        raise TemporalInputError("duplicate observation identifiers")
    items.sort(key=lambda e: (e.observation.timestamp, e.observation.observation_id))
    included: list[ResearchEvidence] = []
    excluded: list[ExcludedEvidence] = []
    reasons: set[str] = set()
    missing: set[str] = set()
    for e in items:
        reason = _exclusion(e, p, at)
        if reason:
            excluded.append(ExcludedEvidence(evidence=e, reason_codes=(reason,)))
            missing.add(reason)
            if reason.startswith("quality_") or reason == "non_numeric":
                reasons.add("incomplete_valid_sequence")
        else:
            included.append(e)
    times = [e.observation.timestamp for e in included]
    if len(set(times)) != len(times):
        reasons.add("simultaneous_evidence")
        simultaneous = {t for t, count in Counter(times).items() if count > 1}
        for e in included[:]:
            if e.observation.timestamp in simultaneous:
                included.remove(e)
                excluded.append(
                    ExcludedEvidence(
                        evidence=e, reason_codes=("simultaneous_evidence",)
                    )
                )
        times = [e.observation.timestamp for e in included]
    if p.source.compatibility != "exact_identity":
        reasons.add("source_compatibility_unavailable")
    if len(included) < p.minimum_observations:
        reasons.add("insufficient_evidence")
        missing.add("insufficient_evidence")
    if times:
        if (at - times[-1]).total_seconds() > p.source.maximum_age_seconds:
            reasons.add("stale_observations")
            missing.add("stale_observations")
        # Coverage includes window edges: absent early/late samples are not normal.
        edges = [p.event_window.start, *times, p.event_window.end]
        if any(
            (b - a).total_seconds() > p.maximum_gap_seconds
            for a, b in zip(edges, edges[1:], strict=False)
        ):
            reasons.add("observation_gap")
            missing.add("observation_gap")
    values = [
        e.observation.measurement.value
        for e in included
        if isinstance(e.observation.measurement, NumericMeasurement)
    ]
    pattern: Pattern = "abstained"
    slope = None
    if not reasons:
        pattern, slope = _describe(values, times, p)
        if pattern == "abstained":
            reasons.add("nonfinite_arithmetic")
    contexts = _contexts(model_contexts, p, at, included)
    limitations = {
        "research_conventions_not_clinical",
        "availability_caller_declared",
        "no_causal_or_exposure_inference",
    }
    limitations.update(r for e in excluded for r in e.reason_codes)
    limitations.update(r for c in contexts for r in c.reason_codes)
    limitations.update(reasons)
    if not contexts:
        missing.add("model_findings_not_supplied")
    elif any(not c.used for c in contexts):
        missing.add("model_findings_unavailable")
    return TemporalSummary(
        schema_version="1.0.0",
        interpretation="research_only",
        method_version="temporal-evidence-1.0.0",
        policy=p,
        assessed_at=at,
        pattern=pattern,
        observation_ids=tuple(e.observation.observation_id for e in included),
        valid_observation_count=len(included),
        event_span=TimeInterval(start=times[0], end=times[-1]) if times else None,
        observed_span_seconds=(times[-1] - times[0]).total_seconds() if times else 0.0,
        slope_per_second=slope,
        supporting_evidence=tuple(included),
        excluded_evidence=tuple(
            sorted(
                excluded,
                key=lambda e: (
                    e.evidence.observation.timestamp,
                    e.evidence.observation.observation_id,
                ),
            )
        ),
        model_contexts=contexts,
        missing_or_unavailable=tuple(sorted(missing)),
        quality_limitations=tuple(sorted(limitations)),
        abstention_reasons=tuple(sorted(reasons)),
    )
