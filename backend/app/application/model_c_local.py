"""Turn transient manual self-reports into a Model C request (pure, no I/O).

Nothing is stored, logged or sent anywhere. Each entry becomes self-reported
Observation v1 records from the declared local entry form. A blank field becomes
an explicit ``not_collected`` record, so missingness stays visible and is never
read as zero. The time convention is documented in
``app.schemas.model_c_local_entry``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from math import ceil

from app.ai.isolation_confinement import (
    DEFAULT_RESEARCH_PARAMETERS,
    assess_isolation_confinement,
)
from app.schemas.baseline import ResearchEvidence, TimeInterval
from app.schemas.isolation_confinement import (
    Indicator,
    IndicatorSource,
    IsolationConfinementAssessment,
    ModelCRequest,
)
from app.schemas.model_c_local_entry import LocalDailyEntry, ModelCLocalSubmission
from app.schemas.observation import (
    AstronautScope,
    CategoricalMeasurement,
    DataQuality,
    NumericMeasurement,
    Observation,
    Provenance,
    UnavailableMeasurement,
)

FORM_ID = "model-c-local-entry-form"
FORM_VERSION = "form-1.0.0"
DATASET_ID = "model-c-local-entry"
# No mission is declared by a manual entry; this label says exactly that.
MISSION_ID = "no-mission-declared"
REPORT_HOUR_UTC = 12
INDICATORS: tuple[Indicator, ...] = ("sleep_duration", "fatigue_self_report")
TIME_CONVENTION = (
    "Each entry dated D is a daily self-report anchored at 12:00 UTC on D. Sleep "
    "duration covers the 24 hours ending at that report, (D-1 12:00, D 12:00] UTC; "
    "fatigue is a point report at 12:00 UTC. The last assessment_days dated "
    "entries form the assessment period; earlier dates form the personal "
    "reference period, declared at least as long as the research parameters need."
)


class LocalEntryError(ValueError):
    """A submission cannot be represented honestly. ``code`` is safe to return."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def report_time(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, REPORT_HOUR_UTC, tzinfo=UTC)


def _quality_and_measurement(
    entry: LocalDailyEntry, metric: str
) -> tuple[
    NumericMeasurement | CategoricalMeasurement | UnavailableMeasurement, DataQuality
]:
    if metric == "sleep_duration" and entry.sleep_duration_hours is not None:
        return (
            NumericMeasurement(
                kind="numeric", value=entry.sleep_duration_hours, unit="h"
            ),
            DataQuality(status="valid"),
        )
    if metric == "fatigue_self_report" and entry.fatigue is not None:
        return (
            CategoricalMeasurement(kind="categorical", value=entry.fatigue),
            DataQuality(status="valid"),
        )
    return (
        UnavailableMeasurement(kind="unavailable", reason="not_collected"),
        DataQuality(status="unavailable", reason_codes=("not_entered",)),
    )


def _evidence(
    submission: ModelCLocalSubmission,
    entry: LocalDailyEntry,
    metric: str,
    run_id: str,
    received_at: datetime,
) -> ResearchEvidence:
    anchor = report_time(entry.date)
    measurement, quality = _quality_and_measurement(entry, metric)
    support = (
        TimeInterval(
            start=anchor - timedelta(days=1) + timedelta(seconds=1), end=anchor
        )
        if metric == "sleep_duration"
        else TimeInterval(start=anchor, end=anchor)
    )
    observation = Observation(
        schema_version="1.0.0",
        observation_id=f"{submission.participant_id}.{metric}.{entry.date.isoformat()}",
        timestamp=anchor,
        ingested_at=received_at,
        domain="behavioral",
        metric=metric,
        scope=AstronautScope(
            kind="astronaut",
            astronaut_id=submission.participant_id,
            mission_id=MISSION_ID,
        ),
        measurement=measurement,
        provenance=Provenance(
            source_type="crew_report",
            source_id=FORM_ID,
            method="manual-daily-entry",
            origin="self_reported",
        ),
        quality=quality,
    )
    return ResearchEvidence(
        observation=observation,
        dataset_id=DATASET_ID,
        run_id=run_id,
        sensor_id=FORM_ID,
        sensor_epoch=FORM_VERSION,
        data_origin="real",
        temporal_support=support,
    )


def build_request(
    submission: ModelCLocalSubmission, received_at: datetime
) -> ModelCRequest:
    """Deterministic for a given submission and server receipt time."""
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise LocalEntryError("server_clock_not_timezone_aware")
    received_at = received_at.astimezone(UTC)
    entries = sorted(submission.entries, key=lambda e: e.date)
    last = entries[-1].date
    if report_time(last) > received_at:
        raise LocalEntryError("entry_after_report_time")
    params = DEFAULT_RESEARCH_PARAMETERS
    first_assessment_day = last - timedelta(days=submission.assessment_days - 1)
    reference_end = report_time(first_assessment_day) - timedelta(days=1)
    needed = timedelta(
        seconds=max(
            params.minimum_occupied_bins * params.bin_duration_seconds,
            ceil(params.minimum_observed_span_seconds),
        )
    )
    reference_start = min(
        report_time(entries[0].date) - timedelta(days=1), reference_end - needed
    )
    run_id = (
        "session-"
        + sha256(
            f"{submission.participant_id}|{received_at.isoformat()}".encode()
        ).hexdigest()[:24]
    )
    evidence = [
        _evidence(submission, entry, metric, run_id, received_at)
        for entry in entries
        for metric in ("sleep_duration", "fatigue_self_report")
    ]
    return ModelCRequest(
        schema_version="1.0.0",
        interpretation="research_only",
        subject_id=submission.participant_id,
        mission_id=MISSION_ID,
        dataset_id=DATASET_ID,
        run_id=run_id,
        data_origin="real",
        assessed_at=received_at,
        reference_interval=TimeInterval(start=reference_start, end=reference_end),
        assessment_interval=TimeInterval(start=reference_end, end=report_time(last)),
        sources=tuple(
            IndicatorSource(
                indicator=indicator,
                instrument_kind="self_report_form",
                source_id=FORM_ID,
                sensor_id=FORM_ID,
                sensor_epoch=FORM_VERSION,
            )
            for indicator in INDICATORS
        ),
        parameters=params,
        evidence=tuple(evidence),
    )


def assess_local_submission(
    submission: ModelCLocalSubmission, received_at: datetime
) -> IsolationConfinementAssessment:
    """Run Model C on one participant's transient entries; nothing is retained."""
    return assess_isolation_confinement(build_request(submission, received_at))
