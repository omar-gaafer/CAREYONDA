"""Read-only source boundary and thin M2 application adapter."""

from dataclasses import dataclass
from typing import Protocol

from app.ai.hazard_reasoning import investigate
from app.features.temporal_features import SampleAnchor
from app.schemas.investigation import Investigation
from app.schemas.observation import Observation


@dataclass(frozen=True)
class EvidencePreset:
    title: str
    current: SampleAnchor
    reference: SampleAnchor
    observations: tuple[Observation, ...]


class EvidenceSource(Protocol):
    def presets(self) -> tuple[EvidencePreset, ...]: ...


class ContextUnavailable(ValueError):
    """Requested source/context is outside the configured local catalog."""


class InvestigationService:
    def __init__(self, source: EvidenceSource) -> None:
        self.source = source

    def run(
        self, current: SampleAnchor, reference: SampleAnchor, window: int
    ) -> Investigation:
        preset = next(
            (
                p
                for p in self.source.presets()
                if p.current == current and p.reference == reference
            ),
            None,
        )
        if preset is None:
            raise ContextUnavailable("Context not configured")
        return investigate(
            preset.observations, current, preset.observations, reference, window
        )
