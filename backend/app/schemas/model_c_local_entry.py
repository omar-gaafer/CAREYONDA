"""Model C local manual-entry contracts (v1.0.0): transient, self-reported only.

A person types daily values for one pseudonymous participant. Only the two
indicators Model C supports are accepted. A blank field stays absent: it becomes
an explicit "not collected" record, never a zero. Nothing here is persisted.

Time convention (declared, not measured): an entry dated ``D`` is a daily report
anchored at 12:00 UTC on ``D``. ``sleep_duration`` describes the 24 hours ending
at that report, i.e. support ``(D-1 12:00, D 12:00]`` UTC at one-second
resolution. ``fatigue_self_report`` is a point report at the anchor.
"""

from __future__ import annotations

import re
from datetime import date as Date
from typing import Annotated, Final, Literal, Self

from pydantic import BeforeValidator, Field, StrictFloat, model_validator

from app.schemas.isolation_confinement import IsolationConfinementAssessment
from app.schemas.observation import Contract

LOCAL_ENTRY_SCHEMA_VERSION: Final = "1.0.0"
MAX_ENTRIES: Final = 60  # keeps a submission well inside the API body limit
MAX_ASSESSMENT_DAYS: Final = 7  # must fit the 7-day reference-age default

# Pseudonym: letters, digits, '-' and '_' only, so e-mail addresses, spaces and
# punctuation-heavy real names are rejected. It cannot prove anonymity.
Pseudonym = Annotated[
    str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$")
]
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _calendar_date(value: object) -> Date:
    """Accept only an ISO calendar date: no epochs, times or time zones."""
    if isinstance(value, Date) and type(value) is Date:
        return value
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError("date must be YYYY-MM-DD")
    return Date.fromisoformat(value)  # rejects impossible dates such as 02-30


CalendarDate = Annotated[Date, BeforeValidator(_calendar_date)]
FatigueCategory = Literal["rested", "tired", "very_tired"]


def _number(value: object) -> object:
    """JSON numbers only (``7`` and ``7.0``); no booleans or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("sleep duration must be a number of hours")
    return float(value)


# 0-24 h is the physical bound of a 24-hour support window, not a clinical range.
SleepHours = Annotated[
    StrictFloat, BeforeValidator(_number), Field(ge=0, le=24, allow_inf_nan=False)
]


class LocalDailyEntry(Contract):
    """One day's self-report. ``None`` means not entered, never zero."""

    date: CalendarDate
    sleep_duration_hours: SleepHours | None = None
    fatigue: FatigueCategory | None = None

    @model_validator(mode="after")
    def has_a_value(self) -> Self:
        if self.sleep_duration_hours is None and self.fatigue is None:
            raise ValueError("an entry needs at least one supported value")
        return self


class ModelCLocalSubmission(Contract):
    schema_version: Literal["1.0.0"]
    participant_id: Pseudonym
    assessment_days: Annotated[int, Field(strict=True, ge=1, le=MAX_ASSESSMENT_DAYS)]
    entries: Annotated[
        tuple[LocalDailyEntry, ...], Field(min_length=1, max_length=MAX_ENTRIES)
    ]

    @model_validator(mode="after")
    def unique_dates(self) -> Self:
        dates = [e.date for e in self.entries]
        if len(set(dates)) != len(dates):
            raise ValueError("each date may appear once")
        return self


class ModelCLocalResponse(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    correlation_id: str
    source: Literal["transient_local_self_report"] = "transient_local_self_report"
    persistence: Literal["none"] = "none"
    time_convention: str
    result: IsolationConfinementAssessment
