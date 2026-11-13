"""Versioned investigation outputs independent of reasoning implementations."""

from typing import Literal

from pydantic import AwareDatetime, Field

from app.schemas.evidence import EvidenceFinding, EvidenceQualityIssue, EvidenceRelation
from app.schemas.observation import Contract, Identifier

HypothesisId = Literal[
    "baseline", "elevated_co2", "sleep_deprivation", "recent_exercise"
]
Compatibility = Literal["supported", "partial", "mixed", "contradicted", "insufficient"]
InvestigationStatus = Literal[
    "ranked", "ambiguous", "insufficient_evidence", "conflicting_evidence"
]


class HypothesisResult(Contract):
    hypothesis_id: HypothesisId
    rank: int = Field(ge=1)
    compatibility: Compatibility
    expected_relations: dict[Identifier, EvidenceRelation]
    supporting_evidence: tuple[EvidenceFinding, ...]
    contradictory_evidence: tuple[EvidenceFinding, ...]
    missing_evidence: tuple[EvidenceFinding, ...]
    explanation: str
    uncertainty: tuple[str, ...]


class Investigation(Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    engine_version: Literal["reference-rules-1.0.0"] = "reference-rules-1.0.0"
    investigation_id: Identifier
    sample_id: Identifier
    timestamp: AwareDatetime
    reference_sample_id: Identifier
    reference_timestamp: AwareDatetime
    window_seconds: int = Field(gt=0)
    status: InvestigationStatus
    selected_hypothesis: HypothesisId | None
    hypotheses: tuple[HypothesisResult, ...]
    observation_ids: tuple[Identifier, ...]
    reference_observation_ids: tuple[Identifier, ...]
    uncertainty: tuple[str, ...]
    quality_issues: tuple[EvidenceQualityIssue, ...]
    safety_status: Literal["not_evaluated"] = "not_evaluated"
