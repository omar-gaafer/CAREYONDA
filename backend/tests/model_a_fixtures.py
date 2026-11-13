"""SYNTHETIC Model A fixtures. Values are generated, not NASA measurements.

Numbers are arbitrary deterministic draws chosen only to exercise software
behavior; they carry no physiological, environmental, or hazard meaning.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from app.ai.nasa_environment_anomaly import METADATA_COLUMNS, feature_names
from app.features.environmental import ENVIRONMENT_METRICS, environmental_schema

COLUMNS: tuple[str, ...] = (*METADATA_COLUMNS, *feature_names())
SPLIT_SIZES = {"train": 240, "validation": 60, "test": 60}


def synthetic_rows(
    count: int, seed: int, start: datetime, prefix: str
) -> list[list[object]]:
    """Rows in exact CSV column order; first row has structural blanks."""
    rng = np.random.default_rng(seed)
    rows: list[list[object]] = []
    previous: dict[str, float] = {}
    for index in range(count):
        row: list[object] = [
            f"synthetic-{prefix}-{index:05d}",
            (start + timedelta(minutes=5 * index)).isoformat(),
        ]
        for offset, metric in enumerate(ENVIRONMENT_METRICS):
            value = float(10.0 * (offset + 1) + rng.normal(0.0, 1.0))
            delta: object = "" if index == 0 else value - previous[metric]
            previous[metric] = value
            row += [value, value + rng.normal(0.0, 0.2), delta, 6.0, 0.0]
        row.append("" if index == 0 else 300.0 + rng.normal(0.0, 5.0))
        rows.append(row)
    return rows


def record(row: list[object]) -> dict[str, object]:
    return dict(zip(COLUMNS, row, strict=True))


def write_split(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(directory: Path) -> None:
    """(Re)write the manifest so hashes and counts match the files on disk."""
    hashes = {
        path.name: _sha256(path)
        for path in sorted(directory.iterdir())
        if path.name != "manifest.json"
    }
    splits = {}
    for split in SPLIT_SIZES:
        with (directory / f"{split}.csv").open(newline="", encoding="utf-8") as handle:
            splits[split] = {"samples": sum(1 for _ in handle) - 1}
    (directory / "manifest.json").write_text(
        json.dumps(
            {"dataset_version": "synthetic-test", "sha256": hashes, "splits": splits},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def build_dataset(directory: Path, seed: int = 3) -> Path:
    """Write a synthetic chronological split directory shaped like the real one."""
    directory.mkdir(parents=True)
    start = datetime(2030, 1, 1, tzinfo=UTC)
    for offset, (split, size) in enumerate(SPLIT_SIZES.items()):
        split_start = start + timedelta(days=10 * offset)
        write_split(
            directory / f"{split}.csv",
            synthetic_rows(size, seed + offset, split_start, split),
        )
    (directory / "feature_schema.json").write_text(
        json.dumps(environmental_schema(), indent=2, sort_keys=True), encoding="utf-8"
    )
    write_manifest(directory)
    return directory
