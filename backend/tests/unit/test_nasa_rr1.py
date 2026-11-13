"""Synthetic RR-1-shaped fixtures; no sensitive or downloaded data in tests."""

import csv
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.features.environmental import (
    build_environment_features,
    chronological_features,
    environmental_schema,
)
from app.ingestion.nasa_rr1 import NasaCsvError, adapt_csv, compare_summary, read_csv
from app.ingestion.nasa_rr1_export import export_nasa_rr1
from app.schemas.observation import (
    NumericMeasurement,
    Observation,
    UnavailableMeasurement,
)

TELEMETRY_HEADERS = [
    "Controller_Time_GMT",
    "Temp_degC_Ground",
    "Temp_degC_ISS",
    "RH_percent_Ground",
    "RH_percent_ISS",
    "CO2_ppm_Ground",
    "CO2_ppm_ISS",
]
RADIATION_HEADERS = [
    "Date",
    "GCR_Dose_mGy_d",
    "SAA_Dose_mGy_d",
    "Total_Dose_mGy_d",
    "Accumulated_Dose_mGy_d",
]


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def telemetry_rows() -> list[list[str]]:
    start = datetime(2014, 9, 20, 3, 59)
    return [
        [
            (start + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M"),
            "22.00",
            "22.50",
            "40.00",
            "41.00",
            str(400 + i),
            str(2000 + i * 100),
        ]
        for i, offset in enumerate((0, 5, 11, 31, 40, 45, 51, 55))
    ]


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    folder = tmp_path / "raw"
    folder.mkdir()
    write_csv(
        folder / "RR-1_EDA_Telemetry_table.csv", TELEMETRY_HEADERS, telemetry_rows()
    )
    write_csv(
        folder / "RR-1_EDA_Radiation_table.csv",
        RADIATION_HEADERS,
        [
            ["2014-09-21", "0.13", "0.07", "0.20", "0.20"],
            ["2014-09-22", "0.13", "0.08", "0.21", "0.41"],
        ],
    )
    write_csv(
        folder / "RR-1_EDA_Summary_table.csv",
        ["", "Max", "Min", "Mean", "Standard Deviation", "Median"],
        [["CO2 ISS [PPM]", "2700.00", "2000.00", "2350.00", "244.95", "2350.00"]],
    )
    return folder


def telemetry(raw: Path) -> Path:
    return raw / "RR-1_EDA_Telemetry_table.csv"


def test_csv_units_gmt_and_source_provenance(raw: Path) -> None:
    path = telemetry(raw)
    table = adapt_csv(path)
    assert len(table.observations) == 48
    assert len(table.records) == 8
    co2 = next(
        o
        for o in table.observations
        if o.metric == "cabin_co2_concentration" and o.scope.kind == "spacecraft"
    )
    assert isinstance(co2.measurement, NumericMeasurement)
    assert co2.measurement.unit == "ppm"
    assert co2.measurement.value == 2000.0
    assert co2.timestamp == datetime(2014, 9, 20, 3, 59, tzinfo=UTC)
    assert co2.ingested_at is None
    assert co2.provenance.origin == "measured"
    assert co2.provenance.source_type == "mission_log"
    assert co2.provenance.simulation is None
    record = table.records[0]
    assert record.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert record.original_fields["Controller_Time_GMT"] == "2014-09-20 03:59"
    assert co2.observation_id in record.observation_ids
    assert all(
        Observation.model_validate_json(o.model_dump_json()) == o
        for o in table.observations
    )
    headers = table.audit["headers"]
    assert isinstance(headers, tuple)
    assert set(headers) == set(TELEMETRY_HEADERS)
    assert {
        o.measurement.unit
        for o in table.observations
        if isinstance(o.measurement, NumericMeasurement)
    } == {"ppm", "degC", "%"}
    assert not any(o.metric == "cabin_co2_partial_pressure" for o in table.observations)


def test_ground_and_iss_never_paired(raw: Path) -> None:
    table = adapt_csv(telemetry(raw))
    ground = [o for o in table.observations if o.scope.kind == "mission"]
    assert len(ground) == 24
    assert all(o.scope.mission_id == "NASA-RR1-ground-control" for o in ground)
    samples = build_environment_features(table.observations)
    assert samples[0].values["cabin_co2_concentration_value"] == 2000
    assert samples[0].values["cabin_co2_concentration_mean_30m"] == 2000
    ground_ids = {o.observation_id for o in ground}
    assert all(
        not ground_ids.intersection(ids)
        for sample in samples
        for ids in sample.evidence.values()
    )


@pytest.mark.parametrize("raw_value", ["", "NaN", "inf", "-inf", "not-a-number"])
def test_missing_and_malformed_measurements_preserved(
    raw: Path, raw_value: str
) -> None:
    rows = telemetry_rows()
    rows[0][-1] = raw_value
    write_csv(telemetry(raw), TELEMETRY_HEADERS, rows)
    table = adapt_csv(telemetry(raw))
    observation = next(
        o
        for o in table.observations
        if o.metric == "cabin_co2_concentration" and o.scope.kind == "spacecraft"
    )
    assert isinstance(observation.measurement, UnavailableMeasurement)
    assert observation.quality.status == (
        "missing" if raw_value == "" else "unavailable"
    )
    assert table.records[0].original_fields["CO2_ppm_ISS"] == raw_value
    sample = build_environment_features(table.observations)[0]
    assert sample.values["cabin_co2_concentration_value"] is None
    assert sample.values["cabin_co2_concentration_missing"] == 1


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("RH_percent_ISS", "101"),
        ("RH_percent_ISS", "-1"),
        ("CO2_ppm_ISS", "-1"),
        ("Temp_degC_ISS", "-300"),
    ],
)
def test_physical_quality_constraints_no_clinical_thresholds(
    raw: Path, column: str, value: str
) -> None:
    rows = telemetry_rows()
    rows[0][TELEMETRY_HEADERS.index(column)] = value
    write_csv(telemetry(raw), TELEMETRY_HEADERS, rows)
    table = adapt_csv(telemetry(raw))
    record = table.records[0]
    invalid = [
        o
        for o in table.observations
        if o.observation_id in record.observation_ids and o.quality.status == "invalid"
    ]
    assert len(invalid) == 1
    assert isinstance(invalid[0].measurement, NumericMeasurement)
    assert invalid[0].measurement.value == float(value)


def test_bad_timestamp_row_not_silently_lost(raw: Path) -> None:
    rows = telemetry_rows()
    rows[0][0] = "bad-time"
    write_csv(telemetry(raw), TELEMETRY_HEADERS, rows)
    table = adapt_csv(telemetry(raw))
    assert len(table.records) == 8
    assert len(table.observations) == 42
    assert table.records[0].issue_codes == ("invalid_timestamp",)
    assert not table.records[0].observation_ids
    assert table.audit["invalid_timestamp_rows"] == 1


def test_duplicate_timestamps_flagged_not_averaged_as_independent(raw: Path) -> None:
    rows = telemetry_rows()
    rows[1][0] = rows[0][0]
    write_csv(telemetry(raw), TELEMETRY_HEADERS, rows)
    table = adapt_csv(telemetry(raw))
    assert table.audit["duplicate_timestamp_rows"] == 1
    assert sum(o.quality.status == "suspect" for o in table.observations) == 12
    assert len(build_environment_features(table.observations)) == 7
    assert (
        build_environment_features(table.observations)[0].values[
            "cabin_co2_concentration_value"
        ]
        is None
    )


def test_radiation_rates_daily_boundary_and_ambiguous_accumulation(raw: Path) -> None:
    table = adapt_csv(raw / "RR-1_EDA_Radiation_table.csv", radiation=True)
    assert len(table.observations) == 8
    rates = [o for o in table.observations if o.metric.endswith("dose_rate")]
    accumulated = [
        o for o in table.observations if o.metric == "radiation_accumulated_dose"
    ]
    assert len(rates) == 6
    assert all(
        isinstance(o.measurement, NumericMeasurement) and o.measurement.unit == "mGy/d"
        for o in rates
    )
    assert all(o.quality.status == "suspect" for o in rates)
    assert all(o.timestamp.hour == 0 and o.timestamp.tzinfo == UTC for o in rates)
    assert rates[0].timestamp == datetime(2014, 9, 22, tzinfo=UTC)
    assert all(isinstance(o.measurement, UnavailableMeasurement) for o in accumulated)
    assert all(
        o.quality.reason_codes == ("ambiguous_accumulated_unit",) for o in accumulated
    )
    assert table.records[0].original_fields["Accumulated_Dose_mGy_d"] == "0.20"
    assert table.audit["interval_seconds_in_source_order"] == {"86400.0": 1}
    assert not build_environment_features(table.observations)


def test_irregular_sampling_actual_windows_and_no_future(raw: Path) -> None:
    table = adapt_csv(telemetry(raw))
    samples = build_environment_features(table.observations)
    assert samples[2].values["gap_seconds"] == 360
    assert samples[3].values["gap_seconds"] == 1200
    assert samples[3].values["cabin_co2_concentration_mean_30m"] == 2200
    assert samples[3].values["cabin_co2_concentration_count_30m"] == 3
    cutoff = samples[2].timestamp
    past = tuple(o for o in table.observations if o.timestamp <= cutoff)
    assert build_environment_features(past) == samples[:3]
    assert build_environment_features(tuple(reversed(table.observations))) == samples
    lookup = {o.observation_id: o for o in table.observations}
    assert all(
        lookup[oid].timestamp <= sample.timestamp
        for sample in samples
        for ids in sample.evidence.values()
        for oid in ids
    )


def test_splits_reset_evidence_and_no_future_leakage(raw: Path) -> None:
    table = adapt_csv(telemetry(raw))
    splits = chronological_features(table.observations)
    assert [len(splits[name]) for name in ("train", "validation", "test")] == [5, 1, 2]
    assert (
        splits["train"][-1].timestamp
        < splits["validation"][0].timestamp
        < splits["test"][0].timestamp
    )
    evidence = {
        name: {
            oid for sample in samples for ids in sample.evidence.values() for oid in ids
        }
        for name, samples in splits.items()
    }
    assert not evidence["train"] & evidence["validation"]
    assert not evidence["train"] & evidence["test"]
    assert not evidence["validation"] & evidence["test"]
    for samples in splits.values():
        assert samples[0].values["gap_seconds"] is None
        assert samples[0].values["cabin_co2_concentration_delta"] is None
        assert samples[0].values["cabin_co2_concentration_count_30m"] == 1


def test_summary_comparison_matches_and_reports_mismatch(raw: Path) -> None:
    summary = raw / "RR-1_EDA_Summary_table.csv"
    comparisons = compare_summary(
        summary, telemetry(raw), raw / "RR-1_EDA_Radiation_table.csv"
    )
    co2 = [c for c in comparisons if c["label"] == "CO2 ISS [PPM]"]
    assert len(co2) == 5
    assert all(c["status"] == "match_at_printed_precision" for c in co2)
    summary.write_text(summary.read_text().replace("2350.00", "9999.00"))
    assert any(
        c["status"] == "mismatch"
        for c in compare_summary(
            summary, telemetry(raw), raw / "RR-1_EDA_Radiation_table.csv"
        )
    )
    assert comparisons[-1]["status"] == "not_comparable_unit_ambiguity"


def test_exports_deterministic_consistent_and_no_overwrite(
    raw: Path, tmp_path: Path
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    manifest = export_nasa_rr1(raw, first)
    export_nasa_rr1(raw, second)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert manifest["telemetry_observations"] == 48
    assert manifest["radiation_observations"] == 8
    for name, digest in json.loads((first / "manifest.json").read_text())[
        "sha256"
    ].items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == digest
    schema = environmental_schema()
    features = schema["features"]
    assert isinstance(features, list)
    assert len(features) == 16
    assert schema["metadata_columns"] == ["sample_id", "event_time_utc"]
    with (first / "train.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert len(rows[0]) == 18
    assert not any("radiation" in name or "heart_rate" in name for name in rows[0])
    with pytest.raises(FileExistsError):
        export_nasa_rr1(raw, first)


def test_header_and_row_width_validation(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.csv"
    malformed.write_text("a,a\n1,2\n")
    with pytest.raises(NasaCsvError):
        read_csv(malformed)
    malformed.write_text("a,b\n1\n")
    with pytest.raises(NasaCsvError):
        read_csv(malformed)
    malformed.write_text("a,b\n1,2\n")
    with pytest.raises(NasaCsvError):
        adapt_csv(malformed)
