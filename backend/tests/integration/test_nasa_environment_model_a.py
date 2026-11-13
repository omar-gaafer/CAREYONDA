"""Model A train -> persist -> reload -> evaluate, using SYNTHETIC split files."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.storage.nasa_environment_model_store import (
    ModelArtifactError,
    load_model_a,
    read_metadata,
)
from app.training.nasa_environment_model_a import (
    DatasetIntegrityError,
    TrainingConfig,
    TrainingOutcome,
    train_model_a,
)
from tests.model_a_fixtures import (
    COLUMNS,
    SPLIT_SIZES,
    build_dataset,
    record,
    write_manifest,
)

FAST = TrainingConfig(
    n_estimators=25, max_samples=64, stability_seeds=(1,), top_k=3, random_state=5
)


def train(
    tmp_path: Path, name: str = "run", data: Path | None = None
) -> TrainingOutcome:
    data = data or build_dataset(tmp_path / f"data-{name}")
    return train_model_a(data, tmp_path / name, FAST)


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_training_writes_traceable_artifacts(tmp_path: Path) -> None:
    outcome = train(tmp_path)
    files = {path.name for path in outcome.output.iterdir()}
    assert files == {
        "model.joblib",
        "metadata.json",
        "evaluation.json",
        "EVALUATION_REPORT.md",
    }
    metadata = read_metadata(outcome.output)
    assert metadata == outcome.metadata
    assert metadata.dataset.schema_version == "1.0.0"
    assert {name: rec.rows for name, rec in metadata.dataset.splits.items()} == (
        SPLIT_SIZES
    )
    manifest = tmp_path / "data-run" / "manifest.json"
    assert len(metadata.dataset.manifest_sha256) == 64
    assert (
        metadata.dataset.splits["train"].sha256
        == json.loads(manifest.read_text())["sha256"]["train.csv"]
    )
    assert metadata.estimator.params["random_state"] == 5
    assert metadata.estimator.params["n_estimators"] == 25
    assert metadata.estimator.params["contamination"] == "auto"
    assert "scikit-learn" in metadata.estimator.runtime_versions
    assert metadata.threshold is not None
    assert metadata.threshold.selected_on_split == "train"
    assert metadata.threshold.quantile == 0.99
    assert metadata.training_rows_used == SPLIT_SIZES["train"]
    assert metadata.metadata_columns == ("sample_id", "event_time_utc")
    assert "probabilit" in metadata.score_definition
    assert any("ground-truth" in item for item in metadata.limitations)

    evaluation = json.loads((outcome.output / "evaluation.json").read_text())
    assert evaluation["supervised_metrics"] is None
    for split, size in SPLIT_SIZES.items():
        info = evaluation["splits"][split]
        assert info["rows"] == size
        assert info["scored"] + info["abstained"] == size
        assert info["rows_with_imputation"] == 1  # the first row of each split
        # Candidate thresholds are compared on train/validation; never on test.
        expected_candidates = 0 if split == "test" else 5
        assert len(info["threshold_sensitivity"]) == expected_candidates
        assert len(info["top_scores"]) == 3
    assert evaluation["seed_stability"][0]["random_state"] == 1
    report = (outcome.output / "EVALUATION_REPORT.md").read_text(encoding="utf-8")
    assert "Do not commit or publish" in report
    assert "no supervised metric is reported" in report
    forbidden = {"accuracy", "precision", "recall", "f1", "roc_auc", "auc"}
    assert not forbidden & set(evaluation)
    assert not forbidden & set(evaluation["splits"]["test"])


def test_training_is_deterministic(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    first = train_model_a(data, tmp_path / "one", FAST)
    second = train_model_a(data, tmp_path / "two", FAST)
    one = json.loads((first.output / "evaluation.json").read_text())
    two = json.loads((second.output / "evaluation.json").read_text())
    assert one.pop("artifact_sha256") is not None
    assert two.pop("artifact_sha256") is not None
    assert one == two
    assert first.metadata.preprocessing == second.metadata.preprocessing
    assert first.metadata.threshold == second.metadata.threshold


def test_test_split_does_not_influence_fitting(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    baseline = train_model_a(data, tmp_path / "baseline", FAST)
    test_csv = data / "test.csv"
    rows = read_rows(test_csv)
    column = COLUMNS.index("cabin_co2_concentration_value")
    for row in rows[1:]:
        row[column] = str(float(row[column]) * 50.0)
    with test_csv.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    write_manifest(data)
    changed = train_model_a(data, tmp_path / "changed", FAST)
    assert changed.metadata.preprocessing == baseline.metadata.preprocessing
    assert changed.metadata.threshold == baseline.metadata.threshold
    base_eval = baseline.evaluation.splits
    new_eval = changed.evaluation.splits
    assert new_eval["train"] == base_eval["train"]
    assert new_eval["validation"] == base_eval["validation"]
    assert new_eval["test"] != base_eval["test"]


def test_identical_feature_run_is_reported_not_removed(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    rows = read_rows(data / "train.csv")
    for index in range(21, 28):  # rows 20..27 share row 20's feature vector
        rows[index][2:] = rows[20][2:]
    with (data / "train.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    write_manifest(data)
    outcome = train_model_a(data, tmp_path / "out", FAST)
    run = outcome.evaluation.splits["train"].longest_identical_feature_run
    assert run is not None
    assert run.length == 8
    assert run.first_sample_id == rows[20][0]
    assert outcome.metadata.training_rows_used == SPLIT_SIZES["train"]
    assert outcome.evaluation.splits["validation"].longest_identical_feature_run is None


def test_reloaded_model_scores_match_evaluation(tmp_path: Path) -> None:
    outcome = train(tmp_path)
    detector = load_model_a(outcome.output)
    rows = read_rows(tmp_path / "data-run" / "validation.csv")[1:]
    results = detector.score_records([record(list(row)) for row in rows])
    by_id = {r.sample_id: r for r in results}
    for top in outcome.evaluation.splits["validation"].top_scores:
        assert by_id[top.sample_id].anomaly_score == top.anomaly_score
    assert results[0].provenance.artifact_sha256 == outcome.metadata.artifact_sha256
    assert results[0].provenance.model_version == "1.1.0"


def test_tampered_artifact_is_refused(tmp_path: Path) -> None:
    outcome = train(tmp_path)
    artifact = outcome.output / "model.joblib"
    artifact.write_bytes(artifact.read_bytes() + b"\0")
    with pytest.raises(ModelArtifactError, match="SHA-256"):
        load_model_a(outcome.output)


def test_runtime_version_mismatch_is_refused(tmp_path: Path) -> None:
    outcome = train(tmp_path)
    path = outcome.output / "metadata.json"
    payload = json.loads(path.read_text())
    payload["estimator"]["runtime_versions"]["scikit-learn"] = "0.0.0"
    path.write_text(json.dumps(payload))
    with pytest.raises(ModelArtifactError, match="scikit-learn version"):
        load_model_a(outcome.output)


def test_missing_metadata_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactError, match="metadata.json"):
        load_model_a(tmp_path)


def test_hash_mismatch_refuses_training(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    with (data / "train.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(DatasetIntegrityError, match="SHA-256 mismatch: train.csv"):
        train_model_a(data, tmp_path / "out", FAST)
    assert not (tmp_path / "out").exists()


def test_schema_mismatch_refuses_training(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    schema = json.loads((data / "feature_schema.json").read_text())
    schema["features"][0]["unit"] = "Pa"
    (data / "feature_schema.json").write_text(json.dumps(schema))
    write_manifest(data)
    with pytest.raises(DatasetIntegrityError, match="differs from project schema"):
        train_model_a(data, tmp_path / "out", FAST)


def test_overlapping_splits_refused(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    train_rows = read_rows(data / "train.csv")
    validation = read_rows(data / "validation.csv")
    validation[1][1] = train_rows[-1][1]
    with (data / "validation.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(validation)
    write_manifest(data)
    with pytest.raises(DatasetIntegrityError, match="chronological|increasing"):
        train_model_a(data, tmp_path / "out", FAST)


def test_wrong_header_refused(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    rows = read_rows(data / "train.csv")
    rows = [row[:-1] for row in rows]
    with (data / "train.csv").open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    write_manifest(data)
    with pytest.raises(ValueError, match="gap_seconds"):
        train_model_a(data, tmp_path / "out", FAST)


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    data = build_dataset(tmp_path / "data")
    (tmp_path / "out").mkdir()
    with pytest.raises(FileExistsError):
        train_model_a(data, tmp_path / "out", FAST)


def test_cli_entry_point(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    data = build_dataset(tmp_path / "data")
    output = tmp_path / "cli-run"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.training.nasa_environment_model_a",
            "--data-dir",
            str(data),
            "--output",
            str(output),
            "--n-estimators",
            "20",
            "--max-samples",
            "64",
            "--threshold-quantile",
            "0.95",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "backend")},
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(result.stdout)
    assert summary["rows"] == SPLIT_SIZES
    metadata = read_metadata(output)
    assert metadata.threshold is not None and metadata.threshold.quantile == 0.95
    assert summary["artifact_sha256"] == metadata.artifact_sha256
