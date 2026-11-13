"""Opt-in trusted local replay smoke; receipt metadata only, no dataset copies."""

import csv
import hashlib
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.environmental_anomaly import EnvironmentalAnomalyService
from app.features.environmental import environmental_schema
from app.schemas.environmental_anomaly_context import EnvironmentalSample
from app.storage.nasa_environment_model_store import read_metadata


def test_trusted_local_replay_acquisition() -> None:
    if os.environ.get("CAREYONDA_MODEL_A_REPLAY_SMOKE") != "1":
        pytest.skip("Explicit trusted artifact/local dataset opt-in required")
    data = Path(os.environ["CAREYONDA_NASA_DATASET"])
    artifact = Path(os.environ["CAREYONDA_MODEL_A_ARTIFACT"])
    worktree = Path(__file__).resolve().parents[3]
    metadata = read_metadata(artifact)
    manifest_bytes = (data / "manifest.json").read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    assert manifest_hash == metadata.dataset.manifest_sha256
    manifest = json.loads(manifest_bytes)
    for name, expected in manifest["sha256"].items():
        assert Path(name).name == name
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == expected
    schema = environmental_schema()
    assert json.loads((data / "feature_schema.json").read_text()) == schema
    schema_features = schema["features"]
    assert isinstance(schema_features, list)
    test_bytes = (data / "test.csv").read_bytes()
    assert hashlib.sha256(test_bytes).hexdigest() == manifest["sha256"]["test.csv"]
    rows = list(csv.DictReader(io.StringIO(test_bytes.decode())))[:3]
    wanted = {r["sample_id"] for r in rows}
    mappings = {}
    with (data / "feature_evidence.jsonl").open() as handle:
        for line in handle:
            item = json.loads(line)
            if item["sample_id"] in wanted:
                assert item["split"] == "test"
                mappings[item["sample_id"]] = item
    assert set(mappings) == wanted
    needed = {
        oid
        for item in mappings.values()
        for ids in item["feature_observation_ids"].values()
        for oid in ids
    } | {oid for item in mappings.values() for oid in item["current_observation_ids"]}
    observations = {}
    with (data / "telemetry_observations.jsonl").open() as handle:
        for line in handle:
            obs = json.loads(line)
            if obs["observation_id"] in needed:
                assert obs["ingested_at"] is None
                observations[obs["observation_id"]] = obs
    assert set(observations) == needed
    # Recheck source integrity after reads, before recording actual local receipt.
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == expected
    assert (
        hashlib.sha256((data / "manifest.json").read_bytes()).hexdigest()
        == manifest_hash
    )
    acquired_at = datetime.now(
        UTC
    )  # Actual completed local acquisition, OUTSIDE scoring service.
    record_id = "replay-" + uuid4().hex
    receipt_dir = worktree / "artifacts" / "replay_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{record_id}.json"
    receipt = {
        "record_id": record_id,
        "dataset_id": "nasa-rr1-eda-validated",
        "dataset_manifest_sha256": manifest_hash,
        "acquired_at": acquired_at.isoformat(),
        "source_reference": str(receipt_path),
    }
    # This file holds receipt metadata only, not measurements, scores or joblib contents.
    with receipt_path.open("x") as handle:
        json.dump(
            {
                **receipt,
                "acquisition_method": "completed verified local reads for CAREYONDA research replay",
                "source_directory": str(data),
                "historical_source_availability": "unknown",
                "historical_source_ingested_at": None,
            },
            handle,
            indent=2,
        )
    service = EnvironmentalAnomalyService.from_artifact(artifact)
    samples = []
    for row in rows:
        item = mappings[row["sample_id"]]
        ids = {
            oid for values in item["feature_observation_ids"].values() for oid in values
        } | set(item["current_observation_ids"])
        samples.append(
            EnvironmentalSample.model_validate(
                {
                    "sample_id": row["sample_id"],
                    "scope": {
                        "mission_id": "NASA-RR1",
                        "spacecraft_id": "ISS",
                        "data_origin": "real",
                        "dataset_id": receipt["dataset_id"],
                        "run_id": record_id,
                    },
                    "event_time_utc": row["event_time_utc"],
                    "available_at": None,
                    "assessment_mode": "historical_replay",
                    "historical_source_availability": "unknown",
                    "replay_acquired_at": acquired_at,
                    "replay_acquisition": receipt,
                    "transformation_version": "environmental-1.0.0",
                    "features": [
                        {
                            "name": f["name"],
                            "unit": f["unit"],
                            "value": None
                            if row[f["name"]] == ""
                            else float(row[f["name"]]),
                            "observation_ids": item["feature_observation_ids"][
                                f["name"]
                            ],
                        }
                        for f in schema_features
                    ],
                    "observations": [observations[oid] for oid in sorted(ids)],
                }
            )
        )
    assessed_at = datetime.now(UTC)
    results = service.assess(samples, assessed_at=assessed_at)
    assert len(results) == 3
    for sample, result in zip(samples, results, strict=True):
        assert (
            result.model is not None
            and result.model.artifact_sha256 == metadata.artifact_sha256
        )
        assert result.status in {"flagged", "not_flagged"}
        assert (
            result.threshold == metadata.threshold.value
            if metadata.threshold
            else result.threshold is None
        )
        assert result.sample.features == sample.features
        assert result.source_event_time == sample.event_time_utc
        assert result.historical_source_availability == "unknown"
        assert result.evidence_availability_scope == "careyonda_replay"
        assert result.replay_acquired_at == acquired_at <= assessed_at
        assert all(o.ingested_at is None for o in result.sample.observations)
    print(
        json.dumps(
            {
                "receipt_path": str(receipt_path),
                "replay_acquired_at": acquired_at.isoformat(),
                "assessed_at": assessed_at.isoformat(),
                "samples_scored": len(results),
                "first_score": results[0].anomaly_score,
                "threshold": results[0].threshold,
                "first_status": results[0].status,
                "historical_source_availability": "unknown",
            },
            sort_keys=True,
        )
    )
