"""Pure association checks against original M2 evidence; no ranking or causality."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from statistics import fmean

from app.features.temporal_features import FATIGUE_ENCODING
from app.quality.validator import evaluate_quality
from app.schemas.baseline import ResearchEvidence, TimeInterval
from app.schemas.evidence import EvidenceFinding, EvidenceRelation
from app.schemas.hybrid import AssociationRule, HybridPolicy
from app.schemas.investigation import Investigation
from app.schemas.observation import (
    BooleanMeasurement,
    CategoricalMeasurement,
    NumericMeasurement,
)


@dataclass(frozen=True)
class EvidenceIndex:
    records: dict[str, ResearchEvidence]
    ambiguous_ids: frozenset[str]


def index_evidence(
    originals: Sequence[ResearchEvidence],
    temporal: Sequence[ResearchEvidence],
) -> EvidenceIndex:
    """Repeated input IDs are quarantined; shared snapshots across M2/H1 must agree."""
    records: dict[str, ResearchEvidence] = {}
    counts = Counter(e.observation.observation_id for e in originals)
    ambiguous = {oid for oid, count in counts.items() if count > 1}
    for item in (*originals, *temporal):
        oid = item.observation.observation_id
        if oid in records and records[oid] != item:
            ambiguous.add(oid)
        records[oid] = item
    return EvidenceIndex(records, frozenset(ambiguous))


def event_windows(m2: Investigation) -> tuple[TimeInterval, TimeInterval]:
    return (
        TimeInterval(
            start=m2.timestamp - timedelta(seconds=m2.window_seconds), end=m2.timestamp
        ),
        TimeInterval(
            start=m2.reference_timestamp - timedelta(seconds=m2.window_seconds),
            end=m2.reference_timestamp,
        ),
    )


def check_finding(
    finding: EvidenceFinding,
    rule: AssociationRule,
    policy: HybridPolicy,
    m2: Investigation,
    index: EvidenceIndex,
    at: datetime,
) -> tuple[EvidenceRelation | None, tuple[str, ...], bool]:
    """Resolve every reference and check the declared M2 relation without ranking.

    The boolean marks incompatible/ambiguous input, distinct from ordinary missing
    evidence. Numeric comparisons use M2's own empirical reference, never H1's band.
    """
    reasons: set[str] = set()
    incompatible = False
    groups: list[list[ResearchEvidence]] = []
    windows = event_windows(m2)
    allowed = (set(m2.observation_ids), set(m2.reference_observation_ids))
    if finding.metric != rule.source.metric or finding.unit != rule.source.unit:
        return None, ("finding_metric_or_unit_mismatch",), True
    for position, ids in enumerate(
        (finding.observation_ids, finding.reference_observation_ids)
    ):
        group: list[ResearchEvidence] = []
        if len(set(ids)) != len(ids):
            reasons.add("duplicate_evidence_reference")
            incompatible = True
        for oid in sorted(set(ids)):
            if oid not in allowed[position]:
                reasons.add("unbound_m2_evidence_reference")
                incompatible = True
            if oid in index.ambiguous_ids:
                reasons.add("duplicate_or_conflicting_provenance")
                incompatible = True
                continue
            e = index.records.get(oid)
            if e is None:
                reasons.add("missing_original_evidence")
                continue
            obs = e.observation
            if not e.available_at(at, "prospective"):
                reasons.add("evidence_unavailable_at_assessment")
                continue
            if obs.scope != policy.scope or not rule.source.matches(e):
                reasons.add("scope_or_source_mismatch")
                incompatible = True
                continue
            if obs.provenance.origin == "derived":
                reasons.add("derived_provenance_unverified")
                incompatible = True
                continue
            if evaluate_quality(obs).status != "valid":
                reasons.add("nonvalid_evidence")
                continue
            if (
                not windows[position].start
                < e.temporal_support.start
                <= e.temporal_support.end
                <= windows[position].end
            ):
                reasons.add("evidence_outside_m2_window")
                incompatible = True
                continue
            unit = (
                obs.measurement.unit
                if isinstance(obs.measurement, NumericMeasurement)
                else "1"
            )
            if unit != rule.source.unit or obs.metric != rule.source.metric:
                reasons.add("evidence_metric_or_unit_mismatch")
                incompatible = True
                continue
            group.append(e)
        if len({e.observation.timestamp for e in group}) != len(group):
            reasons.add("simultaneous_evidence")
            incompatible = True
        if group:
            age_limit = (
                rule.source.maximum_age_seconds
                if position == 0
                else policy.maximum_reference_age_seconds
            )
            if (
                at - max(e.observation.timestamp for e in group)
            ).total_seconds() > age_limit:
                reasons.add(
                    "stale_current_evidence"
                    if position == 0
                    else "stale_reference_evidence"
                )
        groups.append(group)
    current, reference = groups
    if len(current) < rule.minimum_current_observations:
        reasons.add("insufficient_current_evidence")
    if finding.relation in {"missing", "conflicting"}:
        reasons.add("m2_" + finding.relation)
    if reasons:
        return None, tuple(sorted(reasons)), incompatible
    measurements = [e.observation.measurement for e in current]
    if not measurements:
        return None, ("missing_original_evidence",), False
    if all(isinstance(m, NumericMeasurement) for m in measurements):
        values = [m.value for m in measurements if isinstance(m, NumericMeasurement)]
        ref_values = [
            e.observation.measurement.value
            for e in reference
            if isinstance(e.observation.measurement, NumericMeasurement)
        ]
        if not ref_values or len(ref_values) != len(reference):
            return None, ("missing_numeric_reference",), False
        try:
            value = fmean(values)
        except OverflowError:
            return None, ("nonfinite_statistic",), False
        low, high = min(ref_values), max(ref_values)
        relation: EvidenceRelation = (
            "above_reference"
            if value > high
            else "below_reference"
            if value < low
            else "within_reference"
        )
        if not isfinite(value) or (
            finding.observed_value,
            finding.reference_minimum,
            finding.reference_maximum,
        ) != (value, low, high):
            return None, ("finding_snapshot_disagreement",), True
    else:
        if reference:
            return None, ("unexpected_state_reference",), True
        latest = max(
            current, key=lambda e: e.observation.timestamp
        ).observation.measurement
        if isinstance(latest, BooleanMeasurement):
            relation = "active" if latest.value else "inactive"
            if finding.observed_value != float(latest.value):
                return None, ("finding_snapshot_disagreement",), True
        elif (
            isinstance(latest, CategoricalMeasurement)
            and rule.source.metric == "fatigue_self_report"
        ):
            relation = (
                "rested_reported" if latest.value == "rested" else "fatigue_reported"
            )
            if finding.observed_value != FATIGUE_ENCODING[latest.value]:
                return None, ("finding_snapshot_disagreement",), True
        else:
            return None, ("unsupported_measurement_kind",), True
    if relation != finding.relation:
        return None, ("finding_relation_disagreement",), True
    return relation, (), False
