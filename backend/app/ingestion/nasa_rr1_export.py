"""Export audited local NASA RR-1 observations and chronological ISS features."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from app.features.environmental import chronological_features, environmental_schema
from app.ingestion.nasa_rr1 import adapt_csv, compare_summary, read_csv


def _json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_nasa_rr1(raw: Path, output: Path) -> dict[str, object]:
    telemetry_path = raw / "RR-1_EDA_Telemetry_table.csv"
    radiation_path = raw / "RR-1_EDA_Radiation_table.csv"
    summary_path = raw / "RR-1_EDA_Summary_table.csv"
    telemetry = adapt_csv(telemetry_path)
    radiation = adapt_csv(radiation_path, radiation=True)
    splits = chronological_features(telemetry.observations)
    comparisons = compare_summary(summary_path, telemetry_path, radiation_path)
    output.mkdir(parents=True, exist_ok=False)
    for filename, observations in (
        ("telemetry_observations.jsonl", telemetry.observations),
        ("radiation_observations.jsonl", radiation.observations),
    ):
        with (output / filename).open("w", encoding="utf-8") as handle:
            for observation in observations:
                handle.write(observation.model_dump_json() + "\n")
    with (output / "source_records.jsonl").open("w", encoding="utf-8") as handle:
        for record in (*telemetry.records, *radiation.records):
            handle.write(
                json.dumps(asdict(record), sort_keys=True, allow_nan=False) + "\n"
            )
    for name, samples in splits.items():
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["sample_id", "event_time_utc", *samples[0].values]
            )
            writer.writeheader()
            writer.writerows(
                {
                    "sample_id": sample.sample_id,
                    "event_time_utc": sample.timestamp.isoformat(),
                    **sample.values,
                }
                for sample in samples
            )
    with (output / "feature_evidence.jsonl").open("w", encoding="utf-8") as handle:
        for name, samples in splits.items():
            for sample in samples:
                handle.write(
                    json.dumps(
                        {
                            "sample_id": sample.sample_id,
                            "split": name,
                            "event_time_utc": sample.timestamp.isoformat(),
                            "current_observation_ids": sample.current_observation_ids,
                            "feature_observation_ids": sample.evidence,
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
    summary_headers, summary_rows = read_csv(summary_path)
    audit = {
        "telemetry": telemetry.audit,
        "radiation": radiation.audit,
        "summary": {
            "file": summary_path.name,
            "sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "rows": len(summary_rows),
            "headers": summary_headers,
            "comparisons": comparisons,
        },
        "count_discrepancy": {
            "request_stated_rows": {"telemetry": 12086, "radiation": 38},
            "actual_rows": {
                "telemetry": len(telemetry.records),
                "radiation": len(radiation.records),
            },
            "action": "Preserve all source rows; never drop records to match a stated count.",
        },
        "accumulated_unit": "Unverified; raw column and summary say mGy/day, values look cumulative. Numeric raw values preserved in source_records; typed measurement unavailable and excluded from features.",
    }
    _json(output / "audit.json", audit)
    _json(output / "feature_schema.json", environmental_schema())
    (output / "README.md").write_text(
        "# NASA RR-1 ISS environmental features\n\n"
        "Real ISS experiment-environment telemetry only; no human physiology pairing or anomaly labels. "
        "Raw source files remain under datasets/raw/nasa_eda. Ground-control measurements are adapted under a separate mission scope and never used as ISS features.\n\n"
        "Use train.csv, validation.csv, and test.csv chronologically. Drop sample_id and event_time_utc from predictors; feature_schema.json lists the 16 numeric features. "
        "No scaling, imputation, normality assumption, or model fitting is applied. Fit preprocessing on training only. "
        "Trailing 30-minute windows use actual event times and reset per split, so no evidence crosses split boundaries. Means are sample-weighted, not time-weighted. Empty cells are missing, not zero.\n\n"
        "Controller_Time_GMT is interpreted as UTC+00:00; original timestamp tokens and numeric strings are retained in source_records.jsonl. "
        "No CO2 ppm-to-partial-pressure conversion occurs because paired total pressure is absent. "
        "Radiation is a separate daily series, represented at assumed next-midnight UTC boundaries and flagged suspect for temporal uncertainty. "
        "Accumulated-dose units are ambiguous and were not corrected: raw values remain in the sidecar; typed accumulated observations are unavailable. Radiation is not interpolated or joined into telemetry features.\n\n"
        "See audit.json for raw ranges, intervals, quality counts, and summary comparisons, and docs/architecture/D2_D3_NASA_RR1.md for interpretation and limitations.\n",
        encoding="utf-8",
    )
    manifest: dict[str, object] = {
        "dataset_version": "1.0.0",
        "telemetry_observations": len(telemetry.observations),
        "radiation_observations": len(radiation.observations),
        "feature_count": 16,
        "splits": {
            name: {
                "samples": len(samples),
                "start": samples[0].timestamp.isoformat(),
                "end": samples[-1].timestamp.isoformat(),
            }
            for name, samples in splits.items()
        },
        "sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.iterdir())
            if p.is_file()
        },
    }
    _json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("datasets/raw/nasa_eda"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_nasa_rr1(args.raw, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
