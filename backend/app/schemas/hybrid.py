"""AI-H2 descriptive evidence assessments; never a second investigation/ranker."""

from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from app.schemas.baseline import (
    Ids,
    Positive,
    PositiveCount,
    ResearchContract,
    ResearchEvidence,
    ResearchTime,
    Text,
    TimeInterval,
    Version,
    unique_ids,
)
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext, Hash
from app.schemas.evidence import EvidenceRelation
from app.schemas.fusion import SourceRequirement
from app.schemas.investigation import HypothesisId, Investigation
from app.schemas.observation import Contract, Identifier, Scope
from app.schemas.temporal import Pattern, TemporalSummary

ResearchStatus = Literal[
    "supported_by_available_evidence",
    "contradicted_by_available_evidence",
    "mixed_evidence",
    "insufficient_evidence",
    "incompatible_evidence",
]
Verdict = Literal["supports", "contradicts", "cannot_establish", "incompatible"]


class AssociationRule(Contract):
    """Caller-reviewed descriptive M2 expectation, not a medical/causal rule."""

    rule_id: Identifier
    rule_version: Version
    source_reference: Text
    source: SourceRequirement
    expected_relation: EvidenceRelation
    minimum_current_observations: PositiveCount
    required_temporal_patterns: tuple[Pattern, ...]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        unique_ids(self.required_temporal_patterns)
        if self.expected_relation in {"missing", "conflicting"}:
            raise ValueError("missingness and conflict cannot be positive expectations")
        if set(self.required_temporal_patterns) & {"abstained", "no_pattern"}:
            raise ValueError("absence of a temporal finding cannot establish a claim")
        return self


class HybridPolicy(ResearchContract):
    policy_id: Identifier
    policy_version: Version
    scope: Scope
    hypothesis_id: HypothesisId
    rules: Annotated[tuple[AssociationRule, ...], Field(min_length=1)]
    maximum_reference_age_seconds: Positive
    require_model_context: bool
    association_mode: Literal["exact_scope_only"]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        unique_ids(tuple(r.rule_id for r in self.rules))
        unique_ids(tuple(r.source.metric for r in self.rules))
        if not any(r.required_temporal_patterns for r in self.rules):
            raise ValueError("hybrid evaluation requires an explicit temporal rule")
        return self


class RuleAssessment(Contract):
    rule_id: Identifier
    metric: Identifier
    claim: Text
    expected_relation: EvidenceRelation
    observed_relation: EvidenceRelation | None
    outcome: Verdict
    evidence_ids: Ids
    reference_evidence_ids: Ids
    temporal_pattern: Pattern | None
    event_window: TimeInterval
    reason_codes: Ids
    explanation: Text

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.outcome in {"supports", "contradicts"} and not self.evidence_ids:
            raise ValueError("directional assessment requires observation lineage")
        if (
            self.outcome in {"cannot_establish", "incompatible"}
            and not self.reason_codes
        ):
            raise ValueError("blocked assessment requires reasons")
        return self


class EvidenceExclusion(Contract):
    evidence_ids: Ids
    reason_codes: Annotated[Ids, Field(min_length=1)]


class ModelAssociationTrace(Contract):
    context_sha256: Hash
    evidence_ids: Ids
    eligible_context: bool
    outcome: Literal["cannot_establish"]
    reason_codes: Annotated[Ids, Field(min_length=1)]
    explanation: Text


class HybridAssessment(ResearchContract):
    method_version: Literal["hybrid-evidence-1.0.0"]
    original_investigation: Investigation
    original_m2_sha256: Hash
    hypothesis_id: HypothesisId
    policy: HybridPolicy
    assessed_at: ResearchTime
    temporal_summary: TemporalSummary
    evidence_snapshots: tuple[ResearchEvidence, ...]
    model_contexts: tuple[EnvironmentalAnomalyContext, ...]
    supporting_evidence_ids: Ids
    contradicting_evidence_ids: Ids
    missing_evidence: Ids
    unavailable_or_incompatible_evidence: tuple[EvidenceExclusion, ...]
    relevant_temporal_patterns: tuple[Pattern, ...]
    reasoning_steps: tuple[RuleAssessment, ...]
    model_reasoning_steps: tuple[ModelAssociationTrace, ...]
    status: ResearchStatus
    abstention_reasons: Ids
    limitations: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.original_m2_sha256
            != sha256(
                self.original_investigation.model_dump_json().encode()
            ).hexdigest()
        ):
            raise ValueError("M2 snapshot digest must match the original result")
        if set(self.supporting_evidence_ids) & set(self.contradicting_evidence_ids):
            raise ValueError("one observation cannot supply both directional outcomes")
        snapshots = {e.observation.observation_id for e in self.evidence_snapshots}
        if (
            not set(self.supporting_evidence_ids + self.contradicting_evidence_ids)
            <= snapshots
        ):
            raise ValueError("directional lineage must resolve to source snapshots")
        if self.hypothesis_id != self.policy.hypothesis_id:
            raise ValueError(
                "assessment must preserve the selected original hypothesis"
            )
        if self.hypothesis_id not in {
            h.hypothesis_id for h in self.original_investigation.hypotheses
        }:
            raise ValueError("assessment requires an existing M2 hypothesis")
        if self.assessed_at < self.temporal_summary.assessed_at and self.status not in {
            "insufficient_evidence",
            "incompatible_evidence",
        }:
            raise ValueError("future temporal summaries must be quarantined")
        for outcome, ids in (
            ("supports", self.supporting_evidence_ids),
            ("contradicts", self.contradicting_evidence_ids),
        ):
            expected = {
                i
                for s in self.reasoning_steps
                if s.outcome == outcome
                for i in s.evidence_ids
            }
            if set(ids) != expected:
                raise ValueError("aggregate evidence IDs must match directional traces")
        if self.status == "supported_by_available_evidence" and (
            not self.supporting_evidence_ids
            or self.contradicting_evidence_ids
            or self.missing_evidence
        ):
            raise ValueError(
                "support requires complete uncontradicted descriptive evidence"
            )
        if self.status == "contradicted_by_available_evidence" and (
            not self.contradicting_evidence_ids
            or self.supporting_evidence_ids
            or self.missing_evidence
        ):
            raise ValueError("contradiction requires complete directional evidence")
        if self.status == "mixed_evidence" and not (
            self.supporting_evidence_ids and self.contradicting_evidence_ids
        ):
            raise ValueError("mixed assessment requires both evidence directions")
        if (self.status in {"insufficient_evidence", "incompatible_evidence"}) != bool(
            self.abstention_reasons
        ):
            raise ValueError("abstaining statuses require explicit reasons")
        return self
