"""Explicit local replay acquisition; never invent mission-time availability."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.features.environmental import environmental_schema
from app.schemas.environmental_anomaly_context import (
    EnvironmentalSample,
    EnvironmentalScope,
    FeatureEvidence,
    Hash,
    ReplayAcquisition,
)
from app.schemas.observation import Observation


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sha256: dict[str, Hash]


class FeatureMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: str
    split: str
    event_time_utc: str
    current_observation_ids: tuple[str, ...]
    feature_observation_ids: dict[str, tuple[str, ...]]


class FeatureSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    features: tuple[FeatureDefinition, ...]


class FeatureDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    unit: str


def acquire_replay_catalog(
    data: Path, *, expected_manifest_sha256: str, receipt_directory: Path
) -> tuple[tuple[EnvironmentalSample, ...], Path]:
    """Read exactly three test samples; receipt time is actual completed local read.

    The expected digest comes from separately verified artifact metadata. Only receipt
    metadata is written; measurements stay in their original files and process memory.
    """
    repository = Path(__file__).resolve().parents[3]
    if receipt_directory.resolve().is_relative_to(repository):
        raise ValueError("replay receipts must stay outside the Git worktree")
    raw_manifest = (data / "manifest.json").read_bytes()
    if sha256(raw_manifest).hexdigest() != expected_manifest_sha256:
        raise ValueError("dataset manifest mismatch")
    manifest = DatasetManifest.model_validate_json(raw_manifest)
    for name, digest in manifest.sha256.items():
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("invalid manifest filename")
        if sha256((data / name).read_bytes()).hexdigest() != digest:
            raise ValueError("dataset payload mismatch")
    required = {
        "test.csv",
        "feature_schema.json",
        "feature_evidence.jsonl",
        "telemetry_observations.jsonl",
    }
    if not required <= manifest.sha256.keys():
        raise ValueError("required replay payloads absent")
    schema_bytes = (data / "feature_schema.json").read_bytes()
    if json.loads(schema_bytes) != environmental_schema():
        raise ValueError("environmental feature schema mismatch")
    schema = FeatureSchema.model_validate_json(schema_bytes)
    rows = list(csv.DictReader(io.StringIO((data / "test.csv").read_text())))[:3]
    if len(rows) != 3 or len({row["sample_id"] for row in rows}) != 3:
        raise ValueError("three distinct replay samples required")
    wanted = {row["sample_id"] for row in rows}
    mappings: dict[str, FeatureMapping] = {}
    with (data / "feature_evidence.jsonl").open() as handle:
        for line in handle:
            mapping = FeatureMapping.model_validate_json(line)
            if mapping.sample_id in wanted:
                if mapping.split != "test" or mapping.sample_id in mappings:
                    raise ValueError("invalid replay lineage mapping")
                mappings[mapping.sample_id] = mapping
    if set(mappings) != wanted:
        raise ValueError("missing replay lineage")
    needed = {
        oid
        for m in mappings.values()
        for ids in m.feature_observation_ids.values()
        for oid in ids
    } | {oid for m in mappings.values() for oid in m.current_observation_ids}
    observations: dict[str, Observation] = {}
    with (data / "telemetry_observations.jsonl").open() as handle:
        for line in handle:
            observation = Observation.model_validate_json(line)
            if observation.observation_id in needed:
                if (
                    observation.observation_id in observations
                    or observation.ingested_at is not None
                ):
                    raise ValueError("ambiguous or unsupported historical availability")
                observations[observation.observation_id] = observation
    if set(observations) != needed:
        raise ValueError("missing replay evidence")
    # Verify again after acquisition, before issuing the factual receipt.
    if (data / "manifest.json").read_bytes() != raw_manifest:
        raise ValueError("dataset changed during acquisition")
    for name, digest in manifest.sha256.items():
        if sha256((data / name).read_bytes()).hexdigest() != digest:
            raise ValueError("dataset changed during acquisition")
    acquired_at = datetime.now(UTC)  # Acquisition boundary, NOT the scoring service.
    receipt_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    record_id = "replay-" + uuid4().hex
    receipt_path = receipt_directory / (record_id + ".json")
    receipt = ReplayAcquisition(
        record_id=record_id,
        dataset_id="nasa-rr1-eda-validated",
        dataset_manifest_sha256=expected_manifest_sha256,
        acquired_at=acquired_at,
        source_reference="careyonda-local-replay:" + record_id,
    )
    samples = []
    for row in rows:
        mapping = mappings[row["sample_id"]]
        if row["event_time_utc"] != mapping.event_time_utc:
            raise ValueError("sample and evidence event time differ")
        ids = {
            oid for values in mapping.feature_observation_ids.values() for oid in values
        } | set(mapping.current_observation_ids)
        samples.append(
            EnvironmentalSample(
                sample_id=row["sample_id"],
                scope=EnvironmentalScope(
                    mission_id="NASA-RR1",
                    spacecraft_id="ISS",
                    data_origin="real",
                    dataset_id=receipt.dataset_id,
                    run_id=record_id,
                ),
                event_time_utc=datetime.fromisoformat(row["event_time_utc"]),
                available_at=None,
                assessment_mode="historical_replay",
                historical_source_availability="unknown",
                replay_acquired_at=acquired_at,
                replay_acquisition=receipt,
                transformation_version="environmental-1.0.0",
                features=tuple(
                    FeatureEvidence(
                        name=f.name,
                        unit=f.unit,
                        value=None if row[f.name] == "" else float(row[f.name]),
                        observation_ids=mapping.feature_observation_ids[f.name],
                    )
                    for f in schema.features
                ),
                observations=tuple(observations[oid] for oid in sorted(ids)),
            )
        )
    with receipt_path.open("x", encoding="utf-8") as handle:
        handle.write(receipt.model_dump_json(indent=2))
    receipt_path.chmod(0o600)
    return tuple(samples), receipt_path
