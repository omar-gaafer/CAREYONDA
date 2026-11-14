"""Local RR-1 CSV adapters and audit. No network access or unit guessing."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import fmean, median, pstdev, stdev

from app.quality.validator import evaluate_quality
from app.schemas.observation import (
    METRIC_REGISTRY,
    DataQuality,
    Measurement,
    MissionScope,
    NumericMeasurement,
    Observation,
    Provenance,
    SpacecraftScope,
    UnavailableMeasurement,
)

TELEMETRY_COLUMNS = (
    ("Temp_degC_Ground", "environment_temperature", "degC", "ground"),
    ("Temp_degC_ISS", "environment_temperature", "degC", "iss"),
    ("RH_percent_Ground", "relative_humidity", "%", "ground"),
    ("RH_percent_ISS", "relative_humidity", "%", "iss"),
    ("CO2_ppm_Ground", "cabin_co2_concentration", "ppm", "ground"),
    ("CO2_ppm_ISS", "cabin_co2_concentration", "ppm", "iss"),
)
RADIATION_COLUMNS = (
    ("GCR_Dose_mGy_d", "radiation_gcr_dose_rate", "mGy/d", "iss"),
    ("SAA_Dose_mGy_d", "radiation_saa_dose_rate", "mGy/d", "iss"),
    ("Total_Dose_mGy_d", "radiation_total_dose_rate", "mGy/d", "iss"),
    ("Accumulated_Dose_mGy_d", "radiation_accumulated_dose", "mGy", "iss"),
)


class NasaCsvError(ValueError):
    """Malformed file layout; errors identify schema issues, not raw values."""


@dataclass(frozen=True)
class SourceRecord:
    source_file: str
    sha256: str
    row_number: int
    original_fields: dict[str, str]
    observation_ids: tuple[str, ...]
    time_interpretation: str
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class AdaptedTable:
    observations: tuple[Observation, ...]
    records: tuple[SourceRecord, ...]
    audit: dict[str, object]


def read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames is None or len(reader.fieldnames) != len(
            set(reader.fieldnames)
        ):
            raise NasaCsvError("CSV requires unique headers")
        headers = tuple(reader.fieldnames)
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise NasaCsvError("CSV row width differs from header width")
            rows.append(
                {
                    key: value
                    for key, value in row.items()
                    if key is not None and value is not None
                }
            )
    return headers, rows


def descriptive(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "Min": min(values) if values else None,
        "Max": max(values) if values else None,
        "Mean": fmean(values) if values else None,
        "Median": median(values) if values else None,
        "Standard Deviation": stdev(values) if len(values) > 1 else None,
        "population_standard_deviation": pstdev(values) if values else None,
    }


def _numeric(raw: str) -> tuple[float | None, str | None]:
    if not raw.strip():
        return None, "missing_value"
    try:
        value = float(raw)
    except ValueError:
        return None, "invalid_numeric"
    return (value, None) if math.isfinite(value) else (None, "nonfinite_numeric")


def adapt_csv(path: Path, *, radiation: bool = False) -> AdaptedTable:
    """Retain raw rows and numeric tokens in sidecar records linked to observations.

    GMT telemetry is explicitly interpreted as UTC+00:00. Radiation date-only
    rows are represented at the following midnight under an assumed UTC daily
    interval, flagged suspect; this is not a claimed instrument event time.
    Accumulated dose remains unavailable until its conflicting unit is verified.
    """
    columns = RADIATION_COLUMNS if radiation else TELEMETRY_COLUMNS
    time_column = "Date" if radiation else "Controller_Time_GMT"
    headers, rows = read_csv(path)
    expected = {time_column, *(column[0] for column in columns)}
    if set(headers) != expected:
        raise NasaCsvError("CSV headers do not match the RR-1 table contract")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    timestamps: list[datetime | None] = []
    for row in rows:
        try:
            parsed = datetime.strptime(
                row[time_column], "%Y-%m-%d" if radiation else "%Y-%m-%d %H:%M"
            ).replace(tzinfo=UTC)
            timestamps.append(parsed + timedelta(days=1) if radiation else parsed)
        except ValueError:
            timestamps.append(None)
    counts = Counter(timestamp for timestamp in timestamps if timestamp is not None)
    observations: list[Observation] = []
    records: list[SourceRecord] = []
    stats: dict[str, object] = {}
    for column, metric, _, _ in columns:
        parsed_values = [_numeric(row[column]) for row in rows]
        values = [
            value
            for value, issue in parsed_values
            if issue is None and value is not None
        ]
        definition = METRIC_REGISTRY[metric]
        physical_invalid = sum(
            (definition.minimum is not None and v < definition.minimum)
            or (definition.maximum is not None and v > definition.maximum)
            for v in values
        )
        stats[column] = {
            **descriptive(values),
            "missing": sum(issue == "missing_value" for _, issue in parsed_values),
            "invalid_numeric": sum(
                issue in {"invalid_numeric", "nonfinite_numeric"}
                for _, issue in parsed_values
            ),
            "physical_invalid": physical_invalid,
        }
    for index, (row, timestamp) in enumerate(
        zip(rows, timestamps, strict=True), start=2
    ):
        ids: list[str] = []
        issues: list[str] = []
        time_policy = (
            "Date-only label; assumed UTC daily interval; event timestamp at following midnight; not an instrument timestamp"
            if radiation
            else "Controller_Time_GMT explicitly interpreted as UTC+00:00; original token retained"
        )
        if timestamp is None:
            issues.append("invalid_timestamp")
        else:
            for column, metric, unit, scope_name in columns:
                value, issue = _numeric(row[column])
                quality = DataQuality(status="valid")
                measurement: Measurement
                if issue is not None:
                    measurement = UnavailableMeasurement(
                        kind="unavailable",
                        reason="not_received"
                        if issue == "missing_value"
                        else "rejected",
                    )
                    quality = DataQuality(
                        status="missing" if issue == "missing_value" else "unavailable",
                        reason_codes=(issue,),
                    )
                elif metric == "radiation_accumulated_dose":
                    measurement = UnavailableMeasurement(
                        kind="unavailable", reason="rejected"
                    )
                    quality = DataQuality(
                        status="unavailable",
                        reason_codes=("ambiguous_accumulated_unit",),
                    )
                else:
                    assert value is not None
                    measurement = NumericMeasurement(
                        kind="numeric", value=value, unit=unit
                    )
                    reasons = []
                    if radiation:
                        reasons.append("daily_timezone_and_boundary_assumed")
                    if counts[timestamp] > 1:
                        reasons.append("duplicate_timestamp")
                    if reasons:
                        quality = DataQuality(
                            status="suspect", reason_codes=tuple(reasons)
                        )
                oid = f"rr1-{digest[:16]}-r{index}-{column}"
                scope = (
                    SpacecraftScope(
                        kind="spacecraft", spacecraft_id="ISS", mission_id="NASA-RR1"
                    )
                    if scope_name == "iss"
                    else MissionScope(
                        kind="mission", mission_id="NASA-RR1-ground-control"
                    )
                )
                observation = Observation(
                    schema_version="1.0.0",
                    observation_id=oid,
                    timestamp=timestamp,
                    domain=METRIC_REGISTRY[metric].domain,
                    metric=metric,
                    scope=scope,
                    measurement=measurement,
                    quality=quality,
                    provenance=Provenance(
                        source_type="mission_log",
                        source_id=f"nasa-rr1-{'radiation' if radiation else 'telemetry'}-{digest[:16]}",
                        method="csv_daily_interval_assumed_utc"
                        if radiation
                        else "csv_controller_gmt",
                        origin="measured",
                    ),
                )
                assessed = evaluate_quality(observation)
                if assessed.status == "invalid":
                    observation = Observation.model_validate(
                        {
                            **observation.model_dump(),
                            "quality": {
                                "status": "invalid",
                                "reason_codes": assessed.reason_codes,
                            },
                        }
                    )
                observations.append(observation)
                ids.append(oid)
        records.append(
            SourceRecord(
                path.name, digest, index, row, tuple(ids), time_policy, tuple(issues)
            )
        )
    valid_times = [timestamp for timestamp in timestamps if timestamp is not None]
    intervals = Counter(
        (b - a).total_seconds()
        for a, b in zip(valid_times, valid_times[1:], strict=False)
    )
    audit: dict[str, object] = {
        "file": path.name,
        "sha256": digest,
        "headers": headers,
        "rows": len(rows),
        "invalid_timestamp_rows": len(rows) - len(valid_times),
        "duplicate_timestamp_rows": sum(count - 1 for count in counts.values()),
        "first_event_time": min(valid_times).isoformat() if valid_times else None,
        "last_event_time": max(valid_times).isoformat() if valid_times else None,
        "source_first_time_token": rows[0][time_column] if rows else None,
        "source_last_time_token": rows[-1][time_column] if rows else None,
        "interval_seconds_in_source_order": {
            str(key): value for key, value in sorted(intervals.items())
        },
        "columns": stats,
        "observation_quality_counts": dict(
            Counter(o.quality.status for o in observations)
        ),
        "units": {
            column: {
                "canonical_candidate": unit,
                "source_header": column,
                "verified": metric != "radiation_accumulated_dose",
            }
            for column, metric, unit, _ in columns
        },
    }
    if radiation:
        complete = all(
            _numeric(row[column])[1] is None
            for row in rows
            for column, _, _, _ in columns
        )
        if complete and rows:
            total_numbers = [float(row["Total_Dose_mGy_d"]) for row in rows]
            accumulated_numbers = [float(row["Accumulated_Dose_mGy_d"]) for row in rows]
            cumulative = []
            running = 0.0
            for value in total_numbers:
                running += value
                cumulative.append(running)
            audit["accumulation_diagnostics"] = {
                "sum_total_column_numeric": round(sum(total_numbers), 8),
                "last_accumulated_column_numeric": accumulated_numbers[-1],
                "maximum_cumulative_numeric_difference": round(
                    max(
                        abs(a - b)
                        for a, b in zip(cumulative, accumulated_numbers, strict=True)
                    ),
                    8,
                ),
                "maximum_component_sum_numeric_difference": round(
                    max(
                        abs(
                            float(row["GCR_Dose_mGy_d"])
                            + float(row["SAA_Dose_mGy_d"])
                            - float(row["Total_Dose_mGy_d"])
                        )
                        for row in rows
                    ),
                    8,
                ),
                "interpretation": "Numeric consistency check only; not proof of accumulated-dose units or integration boundaries. No values adjusted.",
            }
    return AdaptedTable(tuple(observations), tuple(records), audit)


_SUMMARY_COLUMNS = (
    ("CO2 Ground [PPM]", "CO2_ppm_Ground"),
    ("CO2 ISS [PPM]", "CO2_ppm_ISS"),
    ("Relative Humidity Ground [%]", "RH_percent_Ground"),
    ("Relative Humidity ISS [%]", "RH_percent_ISS"),
    ("Temperature Ground [C]", "Temp_degC_Ground"),
    ("Temperature ISS [C]", "Temp_degC_ISS"),
    ("Radiation GCR [mGy/day]", "GCR_Dose_mGy_d"),
    ("Radiation SAA [mGy/day]", "SAA_Dose_mGy_d"),
    ("Radiation Total [mGy/day]", "Total_Dose_mGy_d"),
)


def compare_summary(
    summary: Path, telemetry: Path, radiation: Path
) -> list[dict[str, object]]:
    _, summary_rows = read_csv(summary)
    _, telemetry_rows = read_csv(telemetry)
    _, radiation_rows = read_csv(radiation)
    by_name = {row[""]: row for row in summary_rows}
    comparisons: list[dict[str, object]] = []
    for label, column in _SUMMARY_COLUMNS:
        rows = radiation_rows if column.endswith("mGy_d") else telemetry_rows
        values = [
            value
            for row in rows
            for value, issue in [_numeric(row[column])]
            if value is not None and issue is None
        ]
        computed = descriptive(values)
        if label not in by_name:
            comparisons.append({"label": label, "status": "missing_summary_row"})
            continue
        for statistic in ("Max", "Min", "Mean", "Standard Deviation", "Median"):
            raw = by_name[label][statistic]
            supplied, issue = _numeric(raw)
            actual = computed[statistic]
            # Compare at the summary's printed precision, not a medical tolerance.
            precision = len(raw.partition(".")[2])
            matches = (
                isinstance(actual, (float, int))
                and supplied is not None
                and round(actual, precision) == supplied
            )
            comparisons.append(
                {
                    "label": label,
                    "statistic": statistic,
                    "supplied": supplied,
                    "computed": actual,
                    "status": "match_at_printed_precision"
                    if matches and issue is None
                    else "mismatch",
                    "standard_deviation_definition": "sample (n-1)",
                }
            )
    comparisons.append(
        {
            "label": "Radiation Accumulated [mGy/day]",
            "status": "not_comparable_unit_ambiguity",
            "reason": "Header and summary label a cumulative-looking series as a rate; no confirming local documentation. Raw values retained; no unit correction or feature use.",
        }
    )
    return comparisons
