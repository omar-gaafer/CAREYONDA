"""Synthetic quality tests; physical limits are not clinical thresholds."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.quality.validator import (
    ObservationValidationError,
    evaluate_quality,
    validate_observation,
)
from app.schemas.observation import DataQuality, Observation


def make_payload(value: float = 75.0) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "observation_id": "synthetic-obs",
        "timestamp": "2026-11-13T10:00:00Z",
        "domain": "physiological",
        "metric": "heart_rate",
        "scope": {
            "kind": "astronaut",
            "astronaut_id": "synthetic-crew",
            "mission_id": "synthetic-mission",
        },
        "measurement": {"kind": "numeric", "value": value, "unit": "bpm"},
        "provenance": {
            "source_type": "sensor",
            "source_id": "synthetic-device",
            "method": "synthetic_sample",
            "origin": "measured",
        },
        "quality": {"status": "valid"},
    }


@pytest.mark.parametrize("status", ["suspect", "invalid", "missing", "unavailable"])
def test_limitations_require_reasons(status: str) -> None:
    with pytest.raises(ValidationError):
        DataQuality.model_validate({"status": status})


@pytest.mark.parametrize(
    "quality",
    [
        {"status": "valid", "reason_codes": ["sensor_fault"]},
        {"status": "suspect", "reason_codes": ["fault", "fault"]},
        {
            "status": "missing",
            "reason_codes": ["not_received"],
            "sensor_confidence": 0.8,
        },
    ],
)
def test_contradictory_quality(quality: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DataQuality.model_validate(quality)


@pytest.mark.parametrize("status", ["valid", "suspect", "invalid"])
def test_present_readings_preserved(status: str) -> None:
    payload = make_payload()
    payload["quality"] = {
        "status": status,
        "reason_codes": [] if status == "valid" else ["sensor_fault"],
    }
    observation = validate_observation(payload)
    before = observation.model_dump_json()
    result = evaluate_quality(observation)
    assert result.status == status
    assert observation.model_dump_json() == before
    assert result == evaluate_quality(observation)


@pytest.mark.parametrize("value", [0.0, 1e9])
def test_no_clinical_threshold(value: float) -> None:
    assert evaluate_quality(validate_observation(make_payload(value))).status == "valid"


def test_physical_violation_retains_reading_and_reasons() -> None:
    payload = make_payload(-1.0)
    payload["quality"] = {"status": "suspect", "reason_codes": ["sensor_fault"]}
    observation = validate_observation(payload)
    result = evaluate_quality(observation)
    assert result.status == "invalid"
    assert result.reason_codes == ("sensor_fault", "physical_domain_violation")
    assert observation.measurement.model_dump()["value"] == -1.0
    assert observation.quality.status == "suspect"


@pytest.mark.parametrize(
    ("status", "reason"),
    [("missing", "not_received"), ("unavailable", "sensor_offline")],
)
def test_absence_quality(status: str, reason: str) -> None:
    payload = make_payload()
    payload["measurement"] = {"kind": "unavailable", "reason": reason}
    payload["quality"] = {"status": status, "reason_codes": [reason]}
    assert evaluate_quality(validate_observation(payload)).status == status


@pytest.mark.parametrize(
    ("status", "measurement"),
    [
        ("missing", {"kind": "numeric", "value": 0.0, "unit": "bpm"}),
        ("unavailable", {"kind": "numeric", "value": 0.0, "unit": "bpm"}),
        ("invalid", {"kind": "unavailable", "reason": "rejected"}),
        ("missing", {"kind": "unavailable", "reason": "sensor_offline"}),
        ("unavailable", {"kind": "unavailable", "reason": "not_received"}),
    ],
)
def test_quality_measurement_consistency(
    status: str, measurement: dict[str, object]
) -> None:
    payload = make_payload()
    payload["quality"] = {"status": status, "reason_codes": ["synthetic_reason"]}
    payload["measurement"] = measurement
    with pytest.raises(ObservationValidationError):
        validate_observation(payload)


def test_safe_structured_errors() -> None:
    payload = make_payload()
    payload["measurement"]["value"] = "sensitive-measurement-marker"
    with pytest.raises(ObservationValidationError) as caught:
        validate_observation(payload)
    assert caught.value.issues
    assert caught.value.issues[0].location == ("measurement", "numeric", "value")
    assert caught.value.issues[0].code == "float_type"
    assert "sensitive-measurement-marker" not in str(caught.value)
    assert "sensitive-measurement-marker" not in repr(caught.value.issues)
    assert caught.value.__suppress_context__


def test_valid_boundary_and_roundtrip() -> None:
    observation = validate_observation(make_payload())
    assert observation == Observation.model_validate_json(observation.model_dump_json())


@pytest.mark.parametrize(
    ("domain", "metric", "unit"),
    [
        ("environmental", "ambient_pressure", "Pa"),
        ("radiation", "absorbed_dose", "Gy"),
        ("altered_gravity", "gravity_magnitude", "m/s2"),
    ],
)
@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_physical_boundaries(domain: str, metric: str, unit: str, value: float) -> None:
    payload = make_payload(value)
    payload.update(domain=domain, metric=metric)
    payload["measurement"]["unit"] = unit
    payload["scope"] = {
        "kind": "spacecraft",
        "spacecraft_id": "synthetic-ship",
        "mission_id": "synthetic-mission",
    }
    assessment = evaluate_quality(validate_observation(payload))
    assert assessment.status == ("invalid" if value < 0 else "valid")
