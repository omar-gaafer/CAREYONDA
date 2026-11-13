"""Test the documented repository-root entry point without external services."""

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_config_overrides_and_integrity(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "steps": 2,
                "episodes_per_scenario": 1,
                "missing_probability": 1.0,
                "seed": 99,
            }
        )
    )
    output = tmp_path / "dataset"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "simulator.run_simulation",
            "--config",
            str(config),
            "--seed",
            "0",
            "--window-seconds",
            "60",
            "--output",
            str(output),
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "backend")},
        capture_output=True,
        text=True,
        check=True,
    )
    manifest = json.loads(result.stdout)
    assert manifest == json.loads((output / "manifest.json").read_text())
    assert manifest["config"]["seed"] == 0
    assert manifest["window_seconds"] == 60
    assert manifest["samples"] == 8
    assert manifest["observations"] == 48
    assert manifest["quality_balance"] == {"missing": 48}
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    with (output / "features.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        assert all(
            value == ("1.0" if name.endswith("_missing") else "")
            for name, value in row.items()
            if name != "sample_id"
        )
