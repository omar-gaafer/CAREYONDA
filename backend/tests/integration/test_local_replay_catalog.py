"""Acquisition tests use artificial inputs only, never NASA data or fitted models."""

import csv
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.features.environmental import environmental_schema
from app.real_data_main import create_app
from app.storage.nasa_replay_catalog import acquire_replay_catalog
from tests.environmental_context_fixtures import sample


def dataset(
    path: Path, *, missing_lineage: bool = False, ingestion: bool = False
) -> str:
    path.mkdir()
    sources = [sample(i).model_dump(mode="json") for i in range(3)]
    features = environmental_schema()["features"]
    assert isinstance(features, list)
    rows = []
    mappings = []
    observations = []
    for index, source in enumerate(sources):
        stamp = f"2000-01-01T00:{index * 5:02d}:00+00:00"
        source["event_time_utc"] = stamp
        values = {f["name"]: f["value"] for f in source["features"]}
        rows.append(
            {"sample_id": source["sample_id"], "event_time_utc": stamp, **values}
        )
        mappings.append(
            {
                "sample_id": source["sample_id"],
                "event_time_utc": stamp,
                "split": "test",
                "current_observation_ids": [
                    o["observation_id"] for o in source["observations"]
                ],
                "feature_observation_ids": {
                    f["name"]: f["observation_ids"] for f in source["features"]
                },
            }
        )
        for o in source["observations"]:
            o["timestamp"] = stamp
            o["ingested_at"] = stamp if ingestion else None
            observations.append(o)
    if missing_lineage:
        mappings.pop()
    with (path / "test.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_id", "event_time_utc", *[f["name"] for f in features]],
        )
        writer.writeheader()
        writer.writerows(rows)
    (path / "feature_schema.json").write_text(json.dumps(environmental_schema()))
    (path / "feature_evidence.jsonl").write_text(
        "".join(json.dumps(m) + "\n" for m in mappings)
    )
    (path / "telemetry_observations.jsonl").write_text(
        "".join(json.dumps(o) + "\n" for o in observations)
    )
    manifest = {
        "sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}
    }
    raw = json.dumps(manifest).encode()
    (path / "manifest.json").write_bytes(raw)
    return sha256(raw).hexdigest()


def test_actual_read_receipt_preserves_unknown_source_and_values(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    digest = dataset(data)
    before = {p.name: p.read_bytes() for p in data.iterdir()}
    started = datetime.now(UTC)
    samples, receipt = acquire_replay_catalog(
        data, expected_manifest_sha256=digest, receipt_directory=tmp_path / "receipts"
    )
    assert len(samples) == 3
    assert samples[0].replay_acquired_at is not None
    assert started <= samples[0].replay_acquired_at <= datetime.now(UTC)
    assert samples[0].replay_acquisition is not None
    assert json.loads(receipt.read_text())["dataset_manifest_sha256"] == digest
    assert samples[0].features[0].value == 100.0
    assert all(
        s.assessment_mode == "historical_replay"
        and s.historical_source_availability == "unknown"
        and s.available_at is None
        for s in samples
    )
    assert all(o.ingested_at is None for s in samples for o in s.observations)
    assert all(s.event_time_utc.year == 2000 for s in samples)
    assert {p.name: p.read_bytes() for p in data.iterdir()} == before


@pytest.mark.parametrize("change", ["manifest", "payload", "lineage", "ingestion"])
def test_invalid_acquisition_issues_no_receipt(tmp_path: Path, change: str) -> None:
    data = tmp_path / "data"
    digest = dataset(
        data, missing_lineage=change == "lineage", ingestion=change == "ingestion"
    )
    if change == "manifest":
        digest = "0" * 64
    if change == "payload":
        (data / "test.csv").write_text("tampered")
    receipts = tmp_path / "receipts"
    with pytest.raises(ValueError):
        acquire_replay_catalog(
            data, expected_manifest_sha256=digest, receipt_directory=receipts
        )
    assert not list(receipts.glob("*.json"))


def test_unconfigured_local_factory_keeps_model_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAREYONDA_TRUSTED_LOCAL_MODEL_A", raising=False)
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/health").status_code == 200
        catalog = client.get("/api/v1/environmental/authorized-samples").json()
        assert (
            catalog["model_availability"] == "unavailable" and catalog["samples"] == []
        )
