"""Statistical deviation result contracts. No scoring or threshold inference."""

from __future__ import annotations

from math import isclose
from typing import Literal, Self

from pydantic import model_validator

from app.schemas.baseline import (
    BaselineProfile,
    Finite,
    Ids,
    Nonnegative,
    Positive,
    ResearchContract,
    ResearchEvidence,
    ResearchTime,
    Text,
    Version,
    validate_numeric_metric,
)
from app.schemas.observation import Contract, Identifier, NumericMeasurement


class CalibrationArtifact(Contract):
    artifact_id: Identifier
    artifact_version: Version
    source: Text


class ResearchThreshold(Contract):
    """An explicitly reviewed research threshold, never a clinical cutoff."""

    value: Positive
    comparison: Literal["greater_than", "greater_than_or_equal"]
    approval_reference: Text
    approved_at: ResearchTime
    calibration: CalibrationArtifact


class AnomalyPolicy(ResearchContract):
    policy_id: Identifier
    policy_version: Version
    metric: Identifier
    unit: Text
    score_definition: Literal["absolute_deviation_over_raw_mad"]
    threshold_governance: Literal["unassessed", "approved_research"]
    governance_source: Text
    calibration: CalibrationArtifact | None
    threshold: ResearchThreshold | None

    @model_validator(mode="after")
    def valid_policy(self) -> Self:
        validate_numeric_metric(self.metric, self.unit, personal=True)
        approved = self.threshold_governance == "approved_research"
        if approved != (self.threshold is not None):
            raise ValueError("threshold requires approved research governance")
        if (
            self.threshold is not None
            and self.calibration != self.threshold.calibration
        ):
            raise ValueError("approved threshold must cite the policy calibration")
        return self


class AnomalyFinding(ResearchContract):
    finding_id: Identifier
    policy: AnomalyPolicy
    baseline: BaselineProfile
    evidence: ResearchEvidence
    assessed_at: ResearchTime
    original_value: Finite | None
    signed_deviation: Finite | None
    absolute_deviation: Nonnegative | None
    raw_mad_score: Nonnegative | None
    direction: Literal["above", "below", "equal", "unassessed"]
    score_status: Literal[
        "scored",
        "flat_reference",
        "insufficient_reference",
        "unsupported",
        "invalid_observation",
    ]
    threshold_status: Literal["unassessed", "exceeded", "not_exceeded"]
    evidence_ids: Ids
    profile_lineage_ids: Ids
    quality_limitations: Ids
    explanation: Text
    abstention_reasons: Ids
    method_version: Identifier

    @model_validator(mode="after")
    def valid_finding(self) -> Self:
        p, b, e = self.policy, self.baseline, self.evidence
        obs = e.observation
        if (p.metric, p.unit) != (b.policy.metric, b.policy.unit):
            raise ValueError("anomaly and baseline metric/unit must match")
        if obs.observation_id not in self.evidence_ids:
            raise ValueError("finding lineage must include the target observation")
        if b.profile_id not in self.profile_lineage_ids:
            raise ValueError("finding lineage must include the baseline profile")
        if obs.observation_id in {
            item.observation.observation_id for item in b.included
        }:
            raise ValueError("target observation cannot belong to its own reference")
        if self.assessed_at < b.assessed_at or obs.timestamp > self.assessed_at:
            raise ValueError("finding cannot precede profile or observation")
        if obs.timestamp <= b.policy.reference_interval.end:
            raise ValueError("target must follow the reference interval")
        expected_value = (
            obs.measurement.value
            if isinstance(obs.measurement, NumericMeasurement)
            else None
        )
        if self.original_value != expected_value:
            raise ValueError("original value must preserve the source measurement")
        compatible = (
            b.policy.source_sensor_compatibility == "exact_identity"
            and e.matches(b.policy.source_scope, p.metric, p.unit)
            and e.available_at(self.assessed_at, b.policy.availability_mode)
            and (self.assessed_at - b.policy.reference_interval.end).total_seconds()
            <= b.policy.maximum_reference_age_seconds
        )
        if not compatible and self.score_status != "unsupported":
            raise ValueError("incompatible or unavailable target requires unsupported")
        if obs.quality.status != "valid":
            if self.score_status not in {"invalid_observation", "unsupported"}:
                raise ValueError("non-valid target must abstain")
            if not self.quality_limitations:
                raise ValueError("non-valid target requires quality limitations")
        has_delta = self.signed_deviation is not None
        if has_delta != (self.absolute_deviation is not None):
            raise ValueError("signed and absolute deviation must coexist")
        if has_delta:
            if self.score_status not in {"scored", "flat_reference"}:
                raise ValueError("unusable baseline or target cannot publish deviation")
            if b.median_value is None or self.original_value is None:
                raise ValueError("deviation requires reference and original value")
            assert self.signed_deviation is not None
            assert self.absolute_deviation is not None
            if not isclose(
                self.signed_deviation,
                self.original_value - b.median_value,
                abs_tol=1e-12,
            ):
                raise ValueError("signed deviation contradicts declared values")
            if not isclose(
                self.absolute_deviation, abs(self.signed_deviation), abs_tol=1e-12
            ):
                raise ValueError("absolute deviation contradicts signed deviation")
            direction = (
                "above"
                if self.signed_deviation > 0
                else "below"
                if self.signed_deviation < 0
                else "equal"
            )
            if self.direction != direction:
                raise ValueError("direction contradicts signed deviation")
        elif self.direction != "unassessed":
            raise ValueError("absent deviation requires unassessed direction")
        if self.score_status == "scored":
            if b.status != "ready" or not has_delta or self.raw_mad_score is None:
                raise ValueError(
                    "scored result requires ready profile, deviation and score"
                )
            if self.abstention_reasons:
                raise ValueError("scored finding cannot carry abstention")
            assert b.raw_mad is not None and b.raw_mad > 0
            assert self.absolute_deviation is not None
            if not isclose(
                self.raw_mad_score, self.absolute_deviation / b.raw_mad, abs_tol=1e-12
            ):
                raise ValueError("score contradicts declared raw-MAD definition")
        else:
            if self.raw_mad_score is not None or not self.abstention_reasons:
                raise ValueError("abstention requires null score and reason codes")
            if (
                self.score_status in {"flat_reference", "insufficient_reference"}
                and self.score_status != b.status
            ):
                raise ValueError("score status contradicts baseline status")
        threshold = p.threshold
        if threshold is None or self.raw_mad_score is None:
            if self.threshold_status != "unassessed":
                raise ValueError("no approved threshold or score: decision unassessed")
        else:
            if threshold.approved_at > self.assessed_at:
                raise ValueError("threshold approval cannot follow assessment")
            exceeds = (
                self.raw_mad_score > threshold.value
                if threshold.comparison == "greater_than"
                else self.raw_mad_score >= threshold.value
            )
            expected = "exceeded" if exceeds else "not_exceeded"
            if self.threshold_status != expected:
                raise ValueError("threshold status contradicts approved research rule")
        return self
