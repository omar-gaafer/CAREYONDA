"""Model C manual-entry flow with SYNTHETIC participants and values only."""

from __future__ import annotations

import ast
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.application import model_c_local
from app.application.model_c_local import (
    FORM_ID,
    FORM_VERSION,
    LocalEntryError,
    assess_local_submission,
    build_request,
)
from app.schemas.isolation_confinement import (
    CategoricalIndicatorAssessment,
    IndicatorSource,
    IsolationConfinementAssessment,
    NumericIndicatorAssessment,
)
from app.schemas.model_c_local_entry import ModelCLocalSubmission

FIRST = date(2030, 3, 1)
SLEEP = (7.0, 7.5, 6.8, 7.2, 7.1, 6.9, 7.4, 7.3, 7.0, 6.7, 7.6, 7.2, 7.0, 7.1)


def entries(
    sleep: tuple[float | None, ...] = SLEEP + (5.0, 4.8, 5.2),
    fatigue: tuple[str | None, ...] | None = None,
    start: date = FIRST,
) -> list[dict[str, Any]]:
    fatigue = fatigue or ("rested",) * 10 + ("tired",) * 4 + ("very_tired",) * 3
    rows = []
    for offset, (hours, feeling) in enumerate(zip(sleep, fatigue, strict=True)):
        row: dict[str, Any] = {"date": (start + timedelta(days=offset)).isoformat()}
        if hours is not None:
            row["sleep_duration_hours"] = hours
        if feeling is not None:
            row["fatigue"] = feeling
        rows.append(row)
    return rows


def submission(
    rows: list[dict[str, Any]], participant: str = "pseudo-a1"
) -> ModelCLocalSubmission:
    return ModelCLocalSubmission.model_validate(
        {
            "schema_version": "1.0.0",
            "participant_id": participant,
            "assessment_days": 3,
            "entries": rows,
        }
    )


def received(rows: list[dict[str, Any]], hours_after_last: float = 6) -> datetime:
    last = max(date.fromisoformat(r["date"]) for r in rows)
    return datetime(last.year, last.month, last.day, 12, tzinfo=UTC) + timedelta(
        hours=hours_after_last
    )


def assess(rows: list[dict[str, Any]], **kwargs: Any) -> IsolationConfinementAssessment:
    return assess_local_submission(submission(rows, **kwargs), received(rows))


def sleep_result(result: IsolationConfinementAssessment) -> NumericIndicatorAssessment:
    item = next(i for i in result.indicators if i.indicator == "sleep_duration")
    assert isinstance(item, NumericIndicatorAssessment)
    return item


def fatigue_result(
    result: IsolationConfinementAssessment,
) -> CategoricalIndicatorAssessment:
    item = next(i for i in result.indicators if i.indicator == "fatigue_self_report")
    assert isinstance(item, CategoricalIndicatorAssessment)
    return item


# --------------------------------------------------------------- valid history


def test_multi_day_self_report_history_is_assessed() -> None:
    result = assess(entries())
    sleep = sleep_result(result)
    assert result.status == "assessed"
    assert sleep.baseline.status == "ready"
    assert sleep.summary.below_reference == 3
    assert all(f.threshold_status == "unassessed" for f in sleep.findings)
    assert fatigue_result(result).status == "assessed"
    counts = {c.category: c.assessment_count for c in fatigue_result(result).categories}
    assert counts == {"rested": 0, "tired": 0, "very_tired": 3}
    assert result.data_origin == "real" and result.safety_status == "not_evaluated"


def test_periods_follow_the_declared_time_convention() -> None:
    rows = entries()
    request = build_request(submission(rows), received(rows))
    last_report = datetime(2030, 3, 17, 12, tzinfo=UTC)
    assert request.assessment_interval.end == last_report
    assert request.assessment_interval.start == last_report - timedelta(days=3)
    assert request.reference_interval.end == request.assessment_interval.start
    assert request.reference_interval.start == datetime(2030, 2, 28, 12, tzinfo=UTC)
    sleep = next(
        e for e in request.evidence if e.observation.metric == "sleep_duration"
    )
    assert sleep.temporal_support.end == sleep.observation.timestamp
    assert sleep.temporal_support.start == sleep.observation.timestamp - timedelta(
        days=1
    ) + timedelta(seconds=1)


# ----------------------------------------------------------- self-report semantics


def test_entries_are_self_reports_from_the_form_never_a_device() -> None:
    rows = entries()
    request = build_request(submission(rows), received(rows))
    for e in request.evidence:
        assert e.observation.provenance.origin == "self_reported"
        assert e.observation.provenance.source_type == "crew_report"
        assert (e.sensor_id, e.sensor_epoch) == (FORM_ID, FORM_VERSION)
        assert e.data_origin == "real"
    assert {s.instrument_kind for s in request.sources} == {"self_report_form"}
    result = assess_local_submission(submission(rows), received(rows))
    sleep = sleep_result(result)
    assert sleep.instrument_kind == "self_report_form"
    assert sleep.evidence_provenance == ("self_report",)
    assert "no physical sensor" in sleep.explanation


def test_sensor_source_cannot_carry_self_reported_records() -> None:
    rows = entries()
    request = build_request(submission(rows), received(rows))
    payload = request.model_dump(mode="json")
    payload["sources"][0]["instrument_kind"] = "sensor"
    with pytest.raises(ValidationError, match="contradicts the instrument kind"):
        type(request).model_validate(payload)


@pytest.mark.parametrize(
    ("kind", "sensor", "message"),
    [
        ("sensor", "x", "requires a self_report_form"),
        ("self_report_form", None, "requires its form id and version"),
    ],
)
def test_instrument_kind_rules(kind: str, sensor: str | None, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        IndicatorSource.model_validate(
            {
                "indicator": "fatigue_self_report",
                "instrument_kind": kind,
                "source_id": "form",
                "sensor_id": sensor,
                "sensor_epoch": None if sensor is None else "v1",
            }
        )


# ---------------------------------------------------------------- invalid input


@pytest.mark.parametrize(
    "bad_date",
    ["2030-02-30", "03/01/2030", "2030-03-01T00:00:00", 1893456000, "", None],
)
def test_invalid_dates_are_rejected(bad_date: object) -> None:
    rows = entries()
    rows[0]["date"] = bad_date
    with pytest.raises(ValidationError):
        submission(rows)


@pytest.mark.parametrize(
    "bad_value", [-0.5, 24.5, "7", True, float("nan"), float("inf")]
)
def test_invalid_sleep_values_are_rejected(bad_value: object) -> None:
    rows = entries()
    rows[0]["sleep_duration_hours"] = bad_value
    with pytest.raises(ValidationError):
        submission(rows)


def test_integer_hours_are_accepted_as_numbers() -> None:
    rows = entries()
    rows[0]["sleep_duration_hours"] = 7
    assert submission(rows).entries[0].sleep_duration_hours == 7.0


@pytest.mark.parametrize("bad", ["exhausted", "Tired", "", 2])
def test_unknown_fatigue_categories_are_rejected(bad: object) -> None:
    rows = entries()
    rows[0]["fatigue"] = bad
    with pytest.raises(ValidationError):
        submission(rows)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"date": "2030-03-02"}, "each date may appear once"),
        ({"mood": "low"}, "Extra inputs"),
        (
            {"sleep_duration_hours": None, "fatigue": None},
            "at least one supported value",
        ),
    ],
)
def test_contradictory_extra_or_empty_entries_are_rejected(
    change: dict[str, Any], message: str
) -> None:
    rows = entries()
    rows[0] = {**rows[0], **change}
    for key in [k for k, v in rows[0].items() if v is None]:
        del rows[0][key]
    with pytest.raises(ValidationError, match=message):
        submission(rows)


@pytest.mark.parametrize("participant", ["a@b.com", "John Smith", "ab", "x" * 41, ""])
def test_participant_must_be_a_short_pseudonym(participant: str) -> None:
    with pytest.raises(ValidationError):
        submission(entries(), participant=participant)


def test_future_entries_are_refused_not_backdated() -> None:
    rows = entries()
    with pytest.raises(LocalEntryError) as error:
        build_request(submission(rows), received(rows, hours_after_last=-1))
    assert error.value.code == "entry_after_report_time"


# --------------------------------------------------- missing data and abstention


def test_blank_fields_stay_missing_and_are_never_zero() -> None:
    sleep: list[float | None] = list(SLEEP + (5.0, 4.8, 5.2))
    sleep[2] = None
    sleep[-1] = None
    rows = entries(tuple(sleep))
    request = build_request(submission(rows), received(rows))
    missing = [
        e for e in request.evidence if e.observation.measurement.kind == "unavailable"
    ]
    assert len(missing) == 2
    assert all(e.observation.quality.status == "unavailable" for e in missing)
    result = sleep_result(assess(rows))
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes
        for e in result.baseline.excluded
    }
    assert "measurement_unavailable" in excluded["pseudo-a1.sleep_duration.2030-03-03"]
    last = next(
        f
        for f in result.findings
        if f.evidence.observation.observation_id.endswith("03-17")
    )
    assert last.score_status == "unsupported" and last.original_value is None


def test_short_history_returns_explicit_abstention_not_an_error() -> None:
    rows = entries(
        sleep=(7.0, 7.2, 6.9, 5.0), fatigue=("rested", "rested", "tired", "tired")
    )
    result = assess(rows)
    assert result.status == "abstained"
    assert result.abstention_reasons == ("no_indicator_assessed",)
    sleep = sleep_result(result)
    assert sleep.baseline.status == "insufficient_reference"
    assert sleep.baseline.median_value is None
    assert "insufficient_occupied_bins" in sleep.abstention_reasons
    assert "insufficient_reference_reports" in fatigue_result(result).abstention_reasons


def test_stale_history_abstains_as_too_old() -> None:
    rows = entries()
    result = assess_local_submission(
        submission(rows), received(rows, hours_after_last=24 * 6)
    )
    assert "reference_too_old" in sleep_result(result).abstention_reasons


def test_single_entry_abstains() -> None:
    result = assess([{"date": "2030-03-01", "sleep_duration_hours": 7.0}])
    assert result.status == "abstained"


# ---------------------------------------------------------- participant isolation


def test_two_participants_are_never_mixed() -> None:
    rows = entries()
    shifted = entries(sleep=tuple(v + 1.0 for v in SLEEP) + (8.0, 8.1, 8.2))
    a = assess(rows, participant="pseudo-a1")
    b = assess(shifted, participant="pseudo-b2")
    assert sleep_result(a).baseline.median_value == pytest.approx(7.1)
    assert sleep_result(b).baseline.median_value == pytest.approx(8.1)
    for result, who in ((a, "pseudo-a1"), (b, "pseudo-b2")):
        ids = {
            e.observation.observation_id for e in sleep_result(result).baseline.included
        }
        assert all(i.startswith(who + ".") for i in ids)
        assert result.subject_id == who
    assert a.run_id != b.run_id


def test_service_keeps_no_state_between_submissions() -> None:
    rows = entries()
    first = assess(rows)
    assess(entries(sleep=(1.0,) * 17), participant="pseudo-b2")
    again = assess(rows)
    assert again.model_dump_json() == first.model_dump_json()


# ------------------------------------------------------ no persistence or egress


def test_flow_modules_import_no_storage_network_or_logging() -> None:
    forbidden = {
        "sqlite3",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "logging",
        "pickle",
        "shelve",
        "app.storage",
        "app.api",
        "tempfile",
        "os",
        "io",
    }
    root = Path(model_c_local.__file__).resolve().parents[1]
    for relative in (
        "application/model_c_local.py",
        "schemas/model_c_local_entry.py",
        "ai/isolation_confinement.py",
        "schemas/isolation_confinement.py",
    ):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not {
            n for n in names if n.split(".")[0] in forbidden or n in forbidden
        }, relative
        assert "open(" not in (root / relative).read_text(encoding="utf-8"), relative
