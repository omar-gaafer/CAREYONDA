"""Optional verification of the supplied local files; never downloads data."""

from pathlib import Path

import pytest

from app.ingestion.nasa_rr1 import adapt_csv, compare_summary


def test_supplied_local_rr1_tables() -> None:
    raw = Path(__file__).resolve().parents[3] / "datasets" / "raw" / "nasa_eda"
    if not raw.is_dir():
        pytest.skip("Local NASA RR-1 CSV files are not part of Git")
    telemetry = adapt_csv(raw / "RR-1_EDA_Telemetry_table.csv")
    radiation = adapt_csv(raw / "RR-1_EDA_Radiation_table.csv", radiation=True)
    assert telemetry.audit["rows"] == 12087
    assert radiation.audit["rows"] == 39
    assert telemetry.audit["duplicate_timestamp_rows"] == 0
    assert telemetry.audit["observation_quality_counts"] == {"valid": 72522}
    assert radiation.audit["observation_quality_counts"] == {
        "suspect": 117,
        "unavailable": 39,
    }
    comparisons = compare_summary(
        raw / "RR-1_EDA_Summary_table.csv",
        raw / "RR-1_EDA_Telemetry_table.csv",
        raw / "RR-1_EDA_Radiation_table.csv",
    )
    assert sum(c["status"] == "match_at_printed_precision" for c in comparisons) == 45
    assert comparisons[-1]["status"] == "not_comparable_unit_ambiguity"
