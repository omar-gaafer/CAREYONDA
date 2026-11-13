"""Traceable evidence statements for deterministic reasoning, not diagnoses."""

from typing import Literal

from app.schemas.observation import Contract, Identifier, QualityStatus

EvidenceRelation = Literal[
    "above_reference",
    "below_reference",
    "within_reference",
    "active",
    "inactive",
    "fatigue_reported",
    "rested_reported",
    "missing",
    "conflicting",
]


class EvidenceFinding(Contract):
    metric: Identifier
    relation: EvidenceRelation
    observation_ids: tuple[Identifier, ...]
    reference_observation_ids: tuple[Identifier, ...] = ()
    observed_value: float | None = None
    unit: str
    reference_minimum: float | None = None
    reference_maximum: float | None = None
    explanation: str


class EvidenceQualityIssue(Contract):
    window: Literal["current", "reference"]
    observation_id: Identifier
    metric: Identifier
    status: QualityStatus
    reason_codes: tuple[Identifier, ...]
