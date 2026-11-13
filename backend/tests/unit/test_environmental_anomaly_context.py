"""Sidecar validation uses artificial observations only."""

from datetime import timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.environmental_anomaly_context import EnvironmentalSample
from tests.environmental_context_fixtures import START, sample


def test_sample_utc_and_evidence_roundtrip() -> None:
    value = sample()
    payload = value.model_dump(mode="json")
    payload["event_time_utc"] = START.astimezone(
        timezone(timedelta(hours=2))
    ).isoformat()
    assert EnvironmentalSample.model_validate(payload) == value
    assert EnvironmentalSample.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(
    "change",
    [
        "order",
        "unit",
        "lineage",
        "future_event",
        "future_ingestion",
        "unknown_ingestion",
        "naive",
        "origin",
        "scope",
    ],
)
def test_reject_invalid_sample(change: str) -> None:
    payload = sample().model_dump(mode="json")
    if change == "order":
        payload["features"].reverse()
    elif change == "unit":
        payload["features"][0]["unit"] = "Pa"
    elif change == "lineage":
        payload["features"][0]["observation_ids"] = ["unresolved"]
    elif change == "future_event":
        payload["event_time_utc"] = (START - timedelta(seconds=1)).isoformat()
    elif change == "future_ingestion":
        payload["observations"][0]["ingested_at"] = (
            START + timedelta(days=1)
        ).isoformat()
    elif change == "unknown_ingestion":
        payload["observations"][0]["ingested_at"] = None
    elif change == "naive":
        payload["event_time_utc"] = "2030-01-01T00:00:00"
    elif change == "origin":
        payload["scope"]["data_origin"] = "synthetic"
    else:
        payload["observations"][0]["scope"]["spacecraft_id"] = "GROUND"
    with pytest.raises(ValidationError):
        EnvironmentalSample.model_validate(payload)
