"""Synthetic report-path tests: no NASA data, artifacts or estimator fitting."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.ai.nasa_environment_anomaly import (
    METADATA_COLUMNS,
    NasaEnvironmentAnomalyDetector,
    expected_features,
    fit_preprocessing,
    parse_records,
)
from app.schemas.nasa_environment_model import ModelAMetadata
from app.storage.nasa_environment_model_store import provenance_from
from scripts import analyze_model_a_environmental as analysis
from tests.model_a_fixtures import build_dataset, write_manifest
from tests.unit.test_nasa_environment_anomaly import FirstFeatureEstimator, threshold


def setup_run(
    root: Path, monkeypatch: pytest.MonkeyPatch, *, has_threshold: bool = True
) -> tuple[Path, ModelAMetadata]:
    dataset = build_dataset(root / "synthetic")
    train = analysis._read_csv(dataset / "train.csv")
    (dataset / "feature_evidence.jsonl").write_text(
        json.dumps(
            {
                "sample_id": train[0]["sample_id"],
                "feature_observation_ids": {
                    "cabin_co2_concentration_value": ["synthetic-observation-1"]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_manifest(dataset)
    spec = fit_preprocessing(expected_features(), parse_records(train).matrix)
    metadata = ModelAMetadata.model_validate(
        {
            "model_version": "1.1.0",
            "created_at_utc": datetime(2030, 1, 1, tzinfo=UTC),
            "artifact_file": "model.joblib",
            "artifact_sha256": "0" * 64,
            "dataset": {
                "dataset_name": "synthetic-audit",
                "dataset_version": "synthetic-test",
                "schema_version": "1.0.0",
                "manifest_sha256": analysis._sha256(dataset / "manifest.json"),
                "feature_schema_sha256": analysis._sha256(
                    dataset / "feature_schema.json"
                ),
                "splits": {
                    name: {
                        "file": name + ".csv",
                        "sha256": analysis._sha256(dataset / (name + ".csv")),
                        "rows": len(analysis._read_csv(dataset / (name + ".csv"))),
                    }
                    for name in analysis.SPLIT_ORDER
                },
            },
            "features": expected_features(),
            "metadata_columns": METADATA_COLUMNS,
            "preprocessing": spec,
            "estimator": {
                "class_name": "synthetic-fake",
                "params": {},
                "runtime_versions": {},
            },
            "threshold": threshold(10.0) if has_threshold else None,
            "training_rows_used": len(train),
            "training_rows_excluded": 0,
            "score_definition": "synthetic test score",
            "intended_use": "synthetic tests only",
            "limitations": ("No scientific or clinical interpretation",),
        }
    )
    detector = NasaEnvironmentAnomalyDetector(
        FirstFeatureEstimator(), spec, metadata.threshold, provenance_from(metadata)
    )
    monkeypatch.setattr(analysis, "read_metadata", lambda _: metadata)
    monkeypatch.setattr(analysis, "load_model_a", lambda _: detector)

    def alternatives(
        train_rows: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        preprocessing: Any,
        params: dict[str, Any],
        seed: int,
    ) -> list[float | None]:
        return [float(i) for i in range(len(rows))]

    monkeypatch.setattr(analysis, "_seed_scores", alternatives)
    return dataset, metadata


@pytest.mark.parametrize("has_threshold", [True, False])
def test_report_and_events_preserve_threshold_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_threshold: bool
) -> None:
    dataset, metadata = setup_run(tmp_path, monkeypatch, has_threshold=has_threshold)
    output = tmp_path / "report"
    report = analysis.run_analysis(dataset, tmp_path / "private-artifact", output)
    events = [
        json.loads(line)
        for line in (output / "temporal_events.jsonl").read_text().splitlines()
    ]
    assert report["model"]["threshold_decision_status"] == (
        "assessed" if has_threshold else "unassessed"
    )
    for event in events:
        assert event["contract_version"].endswith(".v2")
        result = event["model_result"]
        if has_threshold:
            assert result["threshold"] == 10.0
            assert result["comparison"] == ">="
            assert result["status"] == (
                "flagged" if result["score"] >= 10 else "not_flagged"
            )
        else:
            assert result["score"] is not None
            assert result["threshold"] is None
            assert result["threshold_method"] is None
            assert result["comparison"] is None
            assert result["status"] == "unassessed"
            assert result["temporal_persistence_2_of_3"] == "unassessed"
    if not has_threshold:
        for split in report["splits"].values():
            assert split["flagged_at_original_threshold"] is None
            assert split["flagged_fraction_of_scored"] is None
            assert split["causal_persistence_2_of_3_flagged"] is None
            assert split["model_a_flagged_episodes"] is None
        for seed in report["random_seed_robustness"].values():
            for split in seed.values():
                assert split["flagged_at_original_threshold"] is None
        assert "unassessed" in (output / "RESEARCH_REPORT.md").read_text()
    for path in output.iterdir():
        assert str(tmp_path) not in path.read_text()
    assert report["model"]["artifact_sha256"] == metadata.artifact_sha256
    assert events[0]["event"]["feature_observation_ids"] == {
        "cabin_co2_concentration_value": ["synthetic-observation-1"]
    }
    assert events[0]["event"]["historical_source_availability"] == "unknown"
    assert events[1]["event"]["feature_observation_ids"] == {}


def test_evidence_integrity_before_artifact_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, _ = setup_run(tmp_path, monkeypatch)
    (dataset / "feature_evidence.jsonl").write_text("tampered", encoding="utf-8")

    def forbidden(_: Path) -> None:
        pytest.fail("must verify evidence before artifact loading")

    monkeypatch.setattr(analysis, "load_model_a", forbidden)
    with pytest.raises(ValueError, match="feature evidence hash"):
        analysis.run_analysis(dataset, tmp_path / "artifact", tmp_path / "output")


def test_cross_split_overlap_rejected_with_updated_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, metadata = setup_run(tmp_path, monkeypatch)
    validation = dataset / "validation.csv"
    rows = validation.read_text().splitlines()
    train = (dataset / "train.csv").read_text().splitlines()
    rows[1] = train[2].replace("synthetic-train", "synthetic-validation")
    validation.write_text("\n".join(rows) + "\n")
    write_manifest(dataset)
    splits = dict(metadata.dataset.splits)
    splits["validation"] = splits["validation"].model_copy(
        update={"sha256": analysis._sha256(validation)}
    )
    dataset_meta = metadata.dataset.model_copy(
        update={
            "splits": splits,
            "manifest_sha256": analysis._sha256(dataset / "manifest.json"),
        }
    )
    monkeypatch.setattr(
        analysis,
        "read_metadata",
        lambda _: metadata.model_copy(update={"dataset": dataset_meta}),
    )
    with pytest.raises(ValueError, match="splits overlap"):
        analysis.run_analysis(dataset, tmp_path / "artifact", tmp_path / "output")


def replace_metadata(
    dataset: Path, metadata: ModelAMetadata, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh synthetic integrity records after an intentional fixture mutation."""
    write_manifest(dataset)
    splits = {
        name: record.model_copy(
            update={"sha256": analysis._sha256(dataset / record.file)}
        )
        for name, record in metadata.dataset.splits.items()
    }
    metadata = metadata.model_copy(
        update={
            "dataset": metadata.dataset.model_copy(
                update={
                    "splits": splits,
                    "manifest_sha256": analysis._sha256(dataset / "manifest.json"),
                }
            )
        }
    )
    monkeypatch.setattr(analysis, "read_metadata", lambda _: metadata)
    monkeypatch.setattr(
        analysis,
        "load_model_a",
        lambda _: NasaEnvironmentAnomalyDetector(
            FirstFeatureEstimator(),
            metadata.preprocessing,
            metadata.threshold,
            provenance_from(metadata),
        ),
    )


def test_threshold_equality_is_flagged_in_serialized_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset, metadata = setup_run(tmp_path, monkeypatch)
    cutoff = float(
        analysis._read_csv(dataset / "train.csv")[0]["cabin_co2_concentration_value"]
    )
    replace_metadata(
        dataset,
        metadata.model_copy(update={"threshold": threshold(cutoff)}),
        monkeypatch,
    )
    output = tmp_path / "report"
    analysis.run_analysis(dataset, tmp_path / "artifact", output)
    first = json.loads((output / "temporal_events.jsonl").read_text().splitlines()[0])
    assert (
        first["model_result"]["score"] == first["model_result"]["threshold"] == cutoff
    )
    assert first["model_result"]["status"] == "flagged"
    assert first["model_result"]["comparison"] == ">="


@pytest.mark.parametrize("has_threshold", [True, False])
def test_missing_measurement_remains_abstained_with_original_event_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_threshold: bool
) -> None:
    import csv

    dataset, metadata = setup_run(tmp_path, monkeypatch, has_threshold=has_threshold)
    path = dataset / "train.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        columns, rows = reader.fieldnames, list(reader)
    original_time = rows[0]["event_time_utc"]
    rows[0]["cabin_co2_concentration_value"] = ""
    rows[0]["cabin_co2_concentration_missing"] = "1"
    with path.open("w", newline="") as handle:
        assert columns is not None
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    replace_metadata(dataset, metadata, monkeypatch)
    output = tmp_path / "report"
    analysis.run_analysis(dataset, tmp_path / "artifact", output)
    first = json.loads((output / "temporal_events.jsonl").read_text().splitlines()[0])
    assert first["event"]["event_time_utc"] == original_time
    assert first["model_result"]["status"] == "abstained"
    assert first["model_result"]["score"] is None
    assert first["event"]["abstention_reasons"]
    assert first["event"]["historical_source_availability"] == "unknown"
    assert "ingested_at" not in first["event"]
    assert "replay_acquired_at" not in first["event"]


@pytest.mark.parametrize("fault", ["duplicate", "bad_ids", "nonobject"])
def test_invalid_or_ambiguous_lineage_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    dataset, metadata = setup_run(tmp_path, monkeypatch)
    path = dataset / "feature_evidence.jsonl"
    first = path.read_text()
    if fault == "duplicate":
        path.write_text(first + first)
    elif fault == "nonobject":
        path.write_text("[]\n")
    else:
        record = json.loads(first)
        record["feature_observation_ids"] = {"co2": [42]}
        path.write_text(json.dumps(record) + "\n")
    replace_metadata(dataset, metadata, monkeypatch)
    with pytest.raises(ValueError, match="feature evidence record"):
        analysis.run_analysis(dataset, tmp_path / "artifact", tmp_path / "out")
