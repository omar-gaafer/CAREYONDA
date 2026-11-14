"""Explicitly configured synthetic catalog; never accepts request-supplied paths."""

import json
from pathlib import Path
from typing import Literal

from app.application.evidence import EvidencePreset
from app.features.temporal_features import SampleAnchor
from app.schemas.observation import Contract, Observation


class PresetRecord(Contract):
    title: str
    context: SampleAnchor
    reference_context: SampleAnchor
    observations: tuple[Observation, ...]


class CatalogRecord(Contract):
    schema_version: Literal["1.0.0"]
    presets: tuple[PresetRecord, ...]


class LocalSyntheticSource:
    def __init__(self, path: Path) -> None:
        record = CatalogRecord.model_validate(json.loads(path.read_text()))
        if any(
            o.provenance.origin != "simulated"
            for p in record.presets
            for o in p.observations
        ):
            raise ValueError("Synthetic catalog contains unsupported origin")
        ids = [o.observation_id for p in record.presets for o in p.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate catalog evidence identifiers")
        self._presets = tuple(
            EvidencePreset(p.title, p.context, p.reference_context, p.observations)
            for p in record.presets
        )

    def presets(self) -> tuple[EvidencePreset, ...]:
        return self._presets
