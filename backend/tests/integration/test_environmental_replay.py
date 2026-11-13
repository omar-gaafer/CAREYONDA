"""Replay policy tests use artificial observations and acquisition receipts only."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.application.environmental_anomaly import (
    EnvironmentalAnomalyInputError,
    EnvironmentalAnomalyService,
)
from app.schemas.environmental_anomaly_context import (
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
)
from tests.environmental_context_fixtures import START, detector, sample

ACQUIRED = START + timedelta(hours=1)


def replay(*, missing: bool = False) -> EnvironmentalSample:
    payload = sample(missing=missing).model_dump()
    for observation in payload["observations"]:
        observation["ingested_at"] = None
    payload.update(
        {
            "assessment_mode": "historical_replay",
            "historical_source_availability": "unknown",
            "available_at": None,
            "replay_acquired_at": ACQUIRED,
            "replay_acquisition": {
                "record_id": "artificial-receipt",
                "dataset_id": payload["scope"]["dataset_id"],
                "dataset_manifest_sha256": "2" * 64,
                "acquired_at": ACQUIRED,
                "source_reference": "artificial test acquisition; not a factual NASA receipt",
            },
        }
    )
    return EnvironmentalSample.model_validate(payload)


def test_live_and_replay_scores_and_original_events_preserved() -> None:
    service = EnvironmentalAnomalyService(detector())
    live = service.assess([sample()], assessed_at=ACQUIRED)[0]
    archived = replay()
    before = archived.model_dump_json()
    result = service.assess([archived], assessed_at=ACQUIRED)[0]
    assert (
        live.anomaly_score,
        live.threshold,
        live.status,
        live.model,
        live.imputed_features,
    ) == (
        result.anomaly_score,
        result.threshold,
        result.status,
        result.model,
        result.imputed_features,
    )
    assert result.schema_version == "1.1.0"
    assert result.assessment_mode == "historical_replay"
    assert result.source_event_time == START == result.sample.event_time_utc
    assert result.replay_acquired_at == result.assessed_at == ACQUIRED
    assert result.historical_source_availability == "unknown"
    assert result.evidence_availability_scope == "careyonda_replay"
    assert all(o.ingested_at is None for o in result.sample.observations)
    assert result.sample.features == live.sample.features
    assert archived.model_dump_json() == before
    assert (
        EnvironmentalAnomalyContext.model_validate_json(result.model_dump_json())
        == result
    )
    assert (
        service.assess([archived], assessed_at=ACQUIRED)[0].model_dump_json()
        == result.model_dump_json()
    )


@pytest.mark.parametrize(
    "change",
    [
        "receipt",
        "time",
        "unknown",
        "source_ingestion",
        "dataset",
        "receipt_time",
        "before_event",
        "source_availability",
    ],
)
def test_replay_requires_consistent_receipt_and_unknown_source(change: str) -> None:
    payload = replay().model_dump()
    if change == "receipt":
        payload["replay_acquisition"] = None
    elif change == "time":
        payload["replay_acquired_at"] = None
    elif change == "unknown":
        payload["historical_source_availability"] = "known"
    elif change == "source_ingestion":
        payload["observations"][0]["ingested_at"] = START
    elif change == "dataset":
        payload["replay_acquisition"]["dataset_id"] = "other"
    elif change == "receipt_time":
        payload["replay_acquisition"]["acquired_at"] = ACQUIRED + timedelta(seconds=1)
    elif change == "before_event":
        payload["replay_acquired_at"] = payload["replay_acquisition"]["acquired_at"] = (
            START - timedelta(seconds=1)
        )
    else:
        payload["available_at"] = ACQUIRED
    with pytest.raises(ValidationError):
        EnvironmentalSample.model_validate(payload)


def test_replay_future_acquisition_rejected_before_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = detector()

    def forbidden(_: object) -> None:
        raise AssertionError("future acquisition reached scoring")

    monkeypatch.setattr(model, "score_records", forbidden)
    with pytest.raises(EnvironmentalAnomalyInputError, match="future-unavailable"):
        EnvironmentalAnomalyService(model).assess(
            [replay()], assessed_at=ACQUIRED - timedelta(seconds=1)
        )


@pytest.mark.parametrize(
    "change",
    ["mode", "scope", "availability", "source_event", "version", "limitations"],
)
def test_replay_sidecar_cannot_be_relabelled_live(change: str) -> None:
    result = EnvironmentalAnomalyService(detector()).assess(
        [replay()], assessed_at=ACQUIRED
    )[0]
    payload = result.model_dump()
    if change == "mode":
        payload["assessment_mode"] = "live"
    elif change == "scope":
        payload["evidence_availability_scope"] = "source_stream"
    elif change == "availability":
        payload["historical_source_availability"] = "known"
    elif change == "source_event":
        payload["source_event_time"] = ACQUIRED
    elif change == "version":
        payload["schema_version"] = "1.0.0"
    else:
        payload["limitations"] = result.limitations[:-2]
    with pytest.raises(ValidationError):
        EnvironmentalAnomalyContext.model_validate(payload)


def test_replay_sample_cannot_become_live_by_changing_mode() -> None:
    payload = replay().model_dump()
    payload["assessment_mode"] = "live"
    with pytest.raises(ValidationError):
        EnvironmentalSample.model_validate(payload)


def test_live_unknown_ingestion_still_rejected() -> None:
    payload = sample().model_dump()
    payload["observations"][0]["ingested_at"] = None
    with pytest.raises(ValidationError):
        EnvironmentalSample.model_validate(payload)


def test_replay_missing_data_still_abstains() -> None:
    result = EnvironmentalAnomalyService(detector()).assess(
        [replay(missing=True)], assessed_at=ACQUIRED
    )[0]
    assert result.status == "abstained" and result.anomaly_score is None
    assert result.abstention_reasons and result.assessment_mode == "historical_replay"


def test_replay_ppm_is_not_pa() -> None:
    payload = replay().model_dump()
    payload["features"][0]["unit"] = "Pa"
    with pytest.raises(ValidationError):
        EnvironmentalSample.model_validate(payload)


def test_previous_live_sidecar_is_readable() -> None:
    payload = (
        EnvironmentalAnomalyService(detector())
        .assess([sample()], assessed_at=ACQUIRED)[0]
        .model_dump()
    )
    payload["schema_version"] = "1.0.0"
    for field in (
        "assessment_mode",
        "historical_source_availability",
        "replay_acquired_at",
        "source_event_time",
        "evidence_availability_scope",
    ):
        payload.pop(field)
    for field in (
        "assessment_mode",
        "historical_source_availability",
        "replay_acquired_at",
        "replay_acquisition",
    ):
        payload["sample"].pop(field)
    previous = EnvironmentalAnomalyContext.model_validate(payload)
    assert previous.schema_version == "1.0.0" and previous.assessment_mode == "live"


def test_replay_with_unavailable_model_preserves_policy() -> None:
    result = EnvironmentalAnomalyService(None, model_state="unavailable").assess(
        [replay()], assessed_at=ACQUIRED
    )[0]
    assert result.status == "abstained" and result.availability == "unavailable"
    assert (
        result.assessment_mode == "historical_replay"
        and result.historical_source_availability == "unknown"
    )
