"""All examples are synthetic; numerical values are not medical thresholds."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.observation import Observation


@pytest.fixture
def payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "observation_id": "synthetic-obs-1",
        "timestamp": "2026-11-13T12:00:00+02:00",
        "ingested_at": "2026-11-13T10:00:01Z",
        "domain": "physiological",
        "metric": "heart_rate",
        "scope": {
            "kind": "astronaut",
            "astronaut_id": "synthetic-crew",
            "mission_id": "synthetic-mission",
        },
        "measurement": {"kind": "numeric", "value": 75.0, "unit": "bpm"},
        "provenance": {
            "source_type": "sensor",
            "source_id": "synthetic-device",
            "method": "synthetic_sample",
            "origin": "measured",
        },
        "quality": {"status": "valid", "sensor_confidence": 0.8},
    }


@pytest.mark.parametrize(
    ("domain", "metric", "scope", "measurement"),
    [
        (
            "physiological",
            "heart_rate",
            "astronaut",
            {"kind": "numeric", "value": 75.0, "unit": "bpm"},
        ),
        (
            "environmental",
            "ambient_pressure",
            "spacecraft",
            {"kind": "numeric", "value": 100000.0, "unit": "Pa"},
        ),
        (
            "environmental",
            "ambient_pressure",
            "compartment",
            {"kind": "numeric", "value": 100000.0, "unit": "Pa"},
        ),
        (
            "radiation",
            "absorbed_dose",
            "astronaut",
            {"kind": "numeric", "value": 0.001, "unit": "Gy"},
        ),
        (
            "behavioral",
            "sleep_state",
            "astronaut",
            {"kind": "categorical", "value": "asleep"},
        ),
        (
            "altered_gravity",
            "gravity_magnitude",
            "spacecraft",
            {"kind": "numeric", "value": 0.0, "unit": "m/s2"},
        ),
        (
            "mission_context",
            "exercise_active",
            "mission",
            {"kind": "boolean", "value": False},
        ),
    ],
)
def test_domains_and_scopes(
    payload: dict[str, Any],
    domain: str,
    metric: str,
    scope: str,
    measurement: dict[str, object],
) -> None:
    payload.update(domain=domain, metric=metric, measurement=measurement)
    scopes = {
        "astronaut": {
            "kind": "astronaut",
            "astronaut_id": "synthetic-crew",
            "mission_id": "synthetic-mission",
        },
        "spacecraft": {
            "kind": "spacecraft",
            "spacecraft_id": "synthetic-ship",
            "mission_id": "synthetic-mission",
        },
        "compartment": {
            "kind": "compartment",
            "spacecraft_id": "synthetic-ship",
            "compartment_id": "synthetic-cabin",
            "mission_id": "synthetic-mission",
        },
        "mission": {"kind": "mission", "mission_id": "synthetic-mission"},
    }
    payload["scope"] = scopes[scope]
    record = Observation.model_validate(payload)
    assert record.scope.kind == scope
    assert Observation.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("missing", "not_received"),
        ("unavailable", "sensor_offline"),
        ("unavailable", "not_collected"),
        ("unavailable", "rejected"),
    ],
)
def test_absent_values(payload: dict[str, Any], status: str, reason: str) -> None:
    payload["measurement"] = {"kind": "unavailable", "reason": reason}
    payload["quality"] = {"status": status, "reason_codes": ["synthetic_absence"]}
    record = Observation.model_validate(payload)
    assert record.measurement.kind == "unavailable"
    assert "value" not in record.measurement.model_dump()


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -float("inf"), True, "75", None, {}, []]
)
def test_invalid_numeric_values(payload: dict[str, Any], value: object) -> None:
    payload["measurement"]["value"] = value
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize("unit", ["Pa", "Hz", "BPM", "", None])
def test_incompatible_units(payload: dict[str, Any], unit: object) -> None:
    payload["measurement"]["unit"] = unit
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-11-13T10:00:00",
        "not-a-time",
        0,
        True,
        None,
        datetime(2026, 11, 13),
        datetime(2026, 11, 13, tzinfo=UTC, fold=1),
    ],
)
def test_invalid_time(payload: dict[str, Any], timestamp: object) -> None:
    payload["timestamp"] = timestamp
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_time_normalized_and_clock_order(payload: dict[str, Any]) -> None:
    record = Observation.model_validate(payload)
    assert record.timestamp == datetime(2026, 11, 13, 10, tzinfo=UTC)
    assert record.timestamp.tzinfo == UTC
    payload["ingested_at"] = "2026-11-13T09:59:59Z"
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "confidence", [-0.01, 1.01, float("nan"), float("inf"), "0.5", True]
)
def test_invalid_confidence(payload: dict[str, Any], confidence: object) -> None:
    payload["quality"]["sensor_confidence"] = confidence
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "scope",
    [
        {"kind": "astronaut", "mission_id": "m"},
        {"kind": "compartment", "mission_id": "m", "compartment_id": "c"},
        {
            "kind": "astronaut",
            "astronaut_id": "a",
            "mission_id": "m",
            "spacecraft_id": "s",
        },
        {"kind": "mission", "mission_id": "m"},
        {"kind": "unknown", "mission_id": "m"},
    ],
)
def test_invalid_scope(payload: dict[str, Any], scope: dict[str, str]) -> None:
    payload["scope"] = scope
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("domain", "radiation"),
        ("metric", "unknown"),
        ("observation_id", " contains spaces"),
        ("observation_id", ""),
        ("schema_version", "2.0.0"),
        ("schema_version", 1),
    ],
)
def test_invalid_identity_and_domain(
    payload: dict[str, Any], field: str, value: object
) -> None:
    payload[field] = value
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_derived_lineage(payload: dict[str, Any]) -> None:
    payload["provenance"] = {
        "source_type": "computation",
        "source_id": "synthetic-transform",
        "method": "synthetic_mean",
        "origin": "derived",
        "parent_observation_ids": ["synthetic-parent"],
        "transformation_version": "1.0.0",
    }
    record = Observation.model_validate(payload)
    assert record.provenance.parent_observation_ids == ("synthetic-parent",)
    assert Observation.model_validate_json(record.model_dump_json()) == record
    payload["provenance"]["parent_observation_ids"] = [payload["observation_id"]]
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_simulation_metadata(payload: dict[str, Any]) -> None:
    payload["provenance"] = {
        "source_type": "simulator",
        "source_id": "synthetic-generator",
        "method": "synthetic_sample",
        "origin": "simulated",
        "simulation": {
            "scenario_id": "synthetic-scenario",
            "run_id": "synthetic-run",
            "generator_version": "1.0.0",
            "seed": 42,
        },
    }
    record = Observation.model_validate(payload)
    assert record.provenance.simulation is not None
    assert record.provenance.simulation.seed == 42
    assert Observation.model_validate_json(record.model_dump_json()) == record
    del payload["provenance"]["simulation"]
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "patch",
    [
        {"origin": "derived", "source_type": "computation"},
        {"source_type": "simulator"},
        {"parent_observation_ids": ["parent"]},
        {
            "origin": "derived",
            "source_type": "computation",
            "parent_observation_ids": ["p", "p"],
            "transformation_version": "v1",
        },
        {
            "simulation": {
                "scenario_id": "s",
                "run_id": "r",
                "generator_version": "v1",
                "seed": 1,
            }
        },
        {"source_id": ""},
        {"method": ""},
    ],
)
def test_malformed_provenance(
    payload: dict[str, Any], patch: dict[str, object]
) -> None:
    payload["provenance"].update(patch)
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "measurement",
    [
        {"kind": "boolean", "value": 1},
        {"kind": "boolean", "value": "false"},
        {"kind": "numeric", "value": 1.0, "unit": "bpm"},
        {"kind": "boolean", "value": False, "unit": "1"},
    ],
)
def test_strict_boolean(
    payload: dict[str, Any], measurement: dict[str, object]
) -> None:
    payload.update(
        domain="mission_context", metric="exercise_active", measurement=measurement
    )
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_categorical_vocabulary(payload: dict[str, Any]) -> None:
    payload.update(
        domain="behavioral",
        metric="sleep_state",
        measurement={"kind": "categorical", "value": "unknown"},
    )
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_repeatability_and_immutability(payload: dict[str, Any]) -> None:
    original = deepcopy(payload)
    first = Observation.model_validate(payload)
    assert (
        first.model_dump_json() == Observation.model_validate(payload).model_dump_json()
    )
    assert payload == original
    with pytest.raises(ValidationError):
        first.metric = "ambient_pressure"


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_confidence_boundaries(payload: dict[str, Any], confidence: float) -> None:
    payload["quality"]["sensor_confidence"] = confidence
    assert Observation.model_validate(payload).quality.sensor_confidence == confidence


def test_unknown_fields_rejected(payload: dict[str, Any]) -> None:
    payload["measurement"]["unexpected"] = "synthetic"
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_self_reported_origin(payload: dict[str, Any]) -> None:
    payload.update(
        domain="behavioral",
        metric="sleep_state",
        measurement={"kind": "categorical", "value": "awake"},
    )
    payload["provenance"] = {
        "source_type": "crew_report",
        "source_id": "synthetic-report",
        "method": "synthetic_checkin",
        "origin": "self_reported",
    }
    assert Observation.model_validate(payload).provenance.origin == "self_reported"


@pytest.mark.parametrize("timestamp", ["0", "1794564000", "2026-02-30T10:00:00Z"])
def test_non_iso_or_impossible_dates(payload: dict[str, Any], timestamp: str) -> None:
    payload["timestamp"] = timestamp
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_optional_ingestion_roundtrip(payload: dict[str, Any]) -> None:
    del payload["ingested_at"]
    observation = Observation.model_validate(payload)
    assert observation.ingested_at is None
    assert observation == Observation.model_validate_json(observation.model_dump_json())


@pytest.mark.parametrize("ingested_at", ["2026-11-13T12:00:01", 1794564001, "invalid"])
def test_invalid_ingestion_time(payload: dict[str, Any], ingested_at: object) -> None:
    payload["ingested_at"] = ingested_at
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize(
    "domain",
    ["environmental", "radiation", "behavioral", "altered_gravity", "mission_context"],
)
def test_incompatible_domain_metric(payload: dict[str, Any], domain: str) -> None:
    payload["domain"] = domain
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize("identifier", ["a" * 129, "astronaut/name", "crew\n", 42])
def test_identifier_constraints(payload: dict[str, Any], identifier: object) -> None:
    payload["scope"]["astronaut_id"] = identifier
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)
