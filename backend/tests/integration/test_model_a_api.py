"""Model A HTTP boundary tests use artificial observations and fake estimators."""

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.environmental_anomaly import EnvironmentalAnomalyResponse
from app.api.security import MAX_BODY_BYTES
from app.application.environmental_anomaly import EnvironmentalAnomalyService
from app.application.environmental_api import ModelABinding
from app.model_a_main import ModelAConfig, create_app
from app.schemas.environmental_anomaly_context import EnvironmentalSample
from tests.environmental_context_fixtures import START, detector, sample
from tests.integration.test_environmental_replay import replay

URL = "/api/v1/environmental/anomaly-context"
ASSESS = START + timedelta(hours=2)
NOW = START + timedelta(days=1)


def payload(*samples: EnvironmentalSample) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "assessed_at": ASSESS.isoformat(),
        "samples": [s.model_dump(mode="json") for s in samples],
    }


def configured(
    samples: tuple[EnvironmentalSample, ...], *, receipts: tuple[Path, ...] = ()
) -> ModelAConfig:
    return ModelAConfig(authorized_samples=samples, replay_receipt_files=receipts)


def fake_loader(_: ModelAConfig) -> ModelABinding:
    return ModelABinding("available", EnvironmentalAnomalyService(detector()))


def test_startup_without_model() -> None:
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/health").status_code == 200
        response = client.post(URL, json=payload(sample()))
        assert response.status_code == 503
        parsed = EnvironmentalAnomalyResponse.model_validate(response.json())
        assert parsed.model_availability == "unavailable" and parsed.contexts == ()
        assert parsed.correlation_id == response.headers["x-correlation-id"]
        assert response.headers["cache-control"] == "no-store"


def test_configured_live_and_correlation() -> None:
    source = sample()
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(
            URL, json=payload(source), headers={"X-Correlation-ID": "client-claim"}
        )
        assert response.status_code == 200
        body = EnvironmentalAnomalyResponse.model_validate(response.json())
        assert body.model_availability == "available"
        assert body.contexts[0].status == "flagged"
        assert body.contexts[0].anomaly_score == body.contexts[0].threshold == 0.5
        assert body.contexts[0].assessment_mode == "live"
        assert (
            body.correlation_id
            == response.headers["x-correlation-id"]
            != "client-claim"
        )


def test_server_verified_replay(tmp_path: Path) -> None:
    source = replay()
    assert source.replay_acquisition is not None
    receipt = tmp_path / "receipt.json"
    receipt.write_text(source.replay_acquisition.model_dump_json())
    with TestClient(
        create_app(
            configured((source,), receipts=(receipt,)),
            model_loader=fake_loader,
            clock=lambda: NOW,
        ),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=payload(source))
        assert response.status_code == 200
        result = EnvironmentalAnomalyResponse.model_validate(response.json()).contexts[
            0
        ]
        assert result.assessment_mode == "historical_replay"
        assert result.historical_source_availability == "unknown"
        assert result.evidence_availability_scope == "careyonda_replay"
        assert all(o.ingested_at is None for o in result.sample.observations)


@pytest.mark.parametrize(
    "change",
    [
        "order",
        "unit",
        "missing_receipt",
        "naive_assessment",
        "extra_artifact",
        "synthetic_scope",
    ],
)
def test_schema_rejection(change: str) -> None:
    source = replay() if change == "missing_receipt" else sample()
    request = payload(source)
    rows = request["samples"]
    assert isinstance(rows, list)
    if change == "order":
        rows[0]["features"].reverse()
    elif change == "unit":
        rows[0]["features"][0]["unit"] = "Pa"
    elif change == "missing_receipt":
        rows[0]["replay_acquisition"] = None
    elif change == "naive_assessment":
        request["assessed_at"] = "2030-01-01T01:00:00"
    elif change == "extra_artifact":
        request["artifact_directory"] = "/private/model.joblib"
    else:
        rows[0]["scope"]["data_origin"] = "synthetic"
    with TestClient(
        create_app(
            configured((sample(),)), model_loader=fake_loader, clock=lambda: NOW
        ),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=request)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        assert "/private/" not in response.text


@pytest.mark.parametrize(
    "change", ["availability", "feature", "source_id", "unknown_sample"]
)
def test_client_cannot_promote_claims_to_trusted_provenance(change: str) -> None:
    source = sample()
    request = payload(source)
    rows = request["samples"]
    assert isinstance(rows, list)
    if change == "availability":
        rows[0]["available_at"] = (START + timedelta(seconds=2)).isoformat()
    elif change == "feature":
        rows[0]["features"][0]["value"] = 111.0
    elif change == "source_id":
        rows[0]["observations"][0]["provenance"]["source_id"] = "forged-source"
    else:
        rows[0]["sample_id"] = "not-authorized"
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=request)
        assert response.status_code == 403
        assert (
            response.json()["error"]["code"]
            == "environmental_provenance_not_authorized"
        )


def test_forged_replay_receipt_rejected(tmp_path: Path) -> None:
    source = replay()
    assert source.replay_acquisition is not None
    receipt = tmp_path / "receipt.json"
    receipt.write_text(source.replay_acquisition.model_dump_json())
    request = payload(source)
    rows = request["samples"]
    assert isinstance(rows, list)
    rows[0]["replay_acquisition"]["source_reference"] = "/etc/not-a-server-receipt"
    with TestClient(
        create_app(
            configured((source,), receipts=(receipt,)),
            model_loader=fake_loader,
            clock=lambda: NOW,
        ),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=request)
        assert response.status_code == 403
        assert "/etc/" not in response.text


def test_missing_server_receipt_fails_closed() -> None:
    source = replay()
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.get("/api/v1/health").status_code == 200
        response = client.post(URL, json=payload(source))
        assert response.status_code == 503 and response.json()["contexts"] == []


@pytest.mark.parametrize("future_assessment", [False, True])
def test_future_unavailable_or_future_assessment(future_assessment: bool) -> None:
    source = sample()
    request = payload(source)
    request["assessed_at"] = (
        NOW + timedelta(seconds=1) if future_assessment else START
    ).isoformat()
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.post(URL, json=request).status_code == 422


def test_missing_measurements_abstain() -> None:
    source = sample(missing=True)
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=payload(source))
        assert response.status_code == 200
        result = response.json()["contexts"][0]
        assert result["status"] == "abstained" and result["anomaly_score"] is None
        assert result["abstention_reasons"]


def test_batch_and_body_limits() -> None:
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert (
            client.post(
                URL,
                content=b" " * (MAX_BODY_BYTES + 1),
                headers={"Content-Type": "application/json"},
            ).status_code
            == 413
        )
        assert client.post(URL, json=payload()).status_code == 422
        # Minimal invalid samples prove the tuple bound without exceeding body size.
        request = {
            "schema_version": "1.0.0",
            "assessed_at": ASSESS.isoformat(),
            "samples": [{}, {}, {}],
        }
        assert client.post(URL, json=request).status_code == 422


def test_incompatible_or_absent_artifact(tmp_path: Path) -> None:
    config = ModelAConfig(artifact_directory=tmp_path)
    for invalid in (False, True):
        if invalid:
            (tmp_path / "metadata.json").write_text("{}")
            (tmp_path / "model.joblib").write_bytes(b"not deserialized")
        with TestClient(create_app(config), base_url="http://127.0.0.1") as client:
            response = client.post(URL, json=payload(sample()))
            assert response.status_code == 503
            assert response.json()["model_availability"] == (
                "incompatible" if invalid else "unavailable"
            )
            assert str(tmp_path) not in response.text


def test_unexpected_errors_sanitized() -> None:
    class Broken:
        def assess(self, samples: object, *, assessed_at: object) -> tuple[()]:
            raise RuntimeError("/private/model.joblib secret traceback")

    def loader(_: ModelAConfig) -> ModelABinding:
        return ModelABinding("available", Broken())

    with TestClient(
        create_app(configured((sample(),)), model_loader=loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
        raise_server_exceptions=False,
    ) as client:
        response = client.post(URL, json=payload(sample()))
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert "private" not in response.text and "traceback" not in response.text
        assert (
            response.json()["error"]["correlation_id"]
            == response.headers["x-correlation-id"]
        )


def test_loader_runs_once_and_existing_investigations_unchanged() -> None:
    calls = []

    def loader(config: ModelAConfig) -> ModelABinding:
        calls.append(config)
        return fake_loader(config)

    with TestClient(
        create_app(configured((sample(),)), model_loader=loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        context = client.get("/api/v1/contexts").json()["presets"][0]
        request = {
            "schema_version": "1.0.0",
            "current": context["current"],
            "reference": context["reference"],
        }
        before = client.post("/api/v1/investigations", json=request).json()
        assert client.post(URL, json=payload(sample())).status_code == 200
        assert client.post(URL, json=payload(sample())).status_code == 200
        assert client.post("/api/v1/investigations", json=request).json() == before
        assert len(calls) == 1


def test_without_optional_model_dependencies_still_starts() -> None:
    import os
    import subprocess
    import sys

    script = """
import importlib.abc
import sys
class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy', 'sklearn', 'joblib'}:
            raise ImportError('Model dependencies intentionally unavailable')
sys.meta_path.insert(0, NoModels())
from app.model_a_main import create_app
from fastapi.testclient import TestClient
with TestClient(create_app(), base_url='http://127.0.0.1') as client:
    assert client.get('/api/v1/health').status_code == 200
assert not {'numpy', 'sklearn', 'joblib'}.intersection(sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )


def test_unchanged_m42_contract_instances() -> None:
    from tests.unit.test_research_contracts import finding, group, profile

    contracts = (finding(), group(), profile())
    before = tuple(value.model_dump_json() for value in contracts)
    with TestClient(
        create_app(
            configured((sample(),)), model_loader=fake_loader, clock=lambda: NOW
        ),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.post(URL, json=payload(sample())).status_code == 200
    assert tuple(value.model_dump_json() for value in contracts) == before


def test_request_length_cap_accepts_two_valid_samples() -> None:
    from pydantic import ValidationError

    from app.api.environmental_anomaly import EnvironmentalAnomalyRequest

    sources = (sample(), sample(1))
    with TestClient(
        create_app(configured(sources), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.post(URL, json=payload(*sources))
        assert response.status_code == 200 and len(response.json()["contexts"]) == 2
    with pytest.raises(ValidationError) as caught:
        EnvironmentalAnomalyRequest.model_validate(payload(*sources, sample(2)))
    assert any(error["type"] == "too_long" for error in caught.value.errors())


def test_invalid_server_receipt_and_catalog_keep_health_available(
    tmp_path: Path,
) -> None:
    source = replay()
    receipt = tmp_path / "receipt.json"
    receipt.write_text("{}")
    with TestClient(
        create_app(
            configured((source,), receipts=(receipt,)),
            model_loader=fake_loader,
            clock=lambda: NOW,
        ),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.get("/api/v1/health").status_code == 200
        response = client.post(URL, json=payload(source))
        assert response.status_code == 503
        assert str(tmp_path) not in response.text


def test_replay_acquisition_after_assessment(tmp_path: Path) -> None:
    source = replay()
    assert source.replay_acquisition is not None
    receipt = tmp_path / "receipt.json"
    receipt.write_text(source.replay_acquisition.model_dump_json())
    request = payload(source)
    request["assessed_at"] = source.event_time_utc.isoformat()
    with TestClient(
        create_app(
            configured((source,), receipts=(receipt,)),
            model_loader=fake_loader,
            clock=lambda: NOW,
        ),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.post(URL, json=request).status_code == 422


def test_safe_reference_discovery_and_assessment(tmp_path: Path) -> None:
    source = replay()
    assert source.replay_acquisition is not None
    receipt = tmp_path / "receipt.json"
    receipt.write_text(source.replay_acquisition.model_dump_json())
    with TestClient(
        create_app(
            configured((source,), receipts=(receipt,)),
            model_loader=fake_loader,
            clock=lambda: NOW,
        ),
        base_url="http://127.0.0.1",
    ) as client:
        listing = client.get("/api/v1/environmental/authorized-samples")
        assert (
            listing.status_code == 200
            and listing.json()["model_availability"] == "available"
        )
        assert str(tmp_path) not in listing.text
        assert "features" not in listing.text and "source_reference" not in listing.text
        reference = listing.json()["samples"][0]
        request = {
            "schema_version": "1.1.0",
            "assessed_at": ASSESS.isoformat(),
            "sample_references": [
                {
                    "sample_id": reference["sample_id"],
                    "assessment_mode": reference["assessment_mode"],
                }
            ],
        }
        result = client.post(URL, json=request)
        assert result.status_code == 200
        assert (
            result.json()["contexts"][0]["sample"]["replay_acquisition"]["record_id"]
            == reference["receipt_id"]
        )
        request = {
            "schema_version": "1.1.0",
            "assessed_at": ASSESS.isoformat(),
            "sample_references": [
                {"sample_id": "forged", "assessment_mode": "historical_replay"}
            ],
        }
        assert client.post(URL, json=request).status_code == 403


def test_reference_request_cannot_override_evidence() -> None:
    with TestClient(
        create_app(
            configured((sample(),)), model_loader=fake_loader, clock=lambda: NOW
        ),
        base_url="http://127.0.0.1",
    ) as client:
        request = {
            "schema_version": "1.1.0",
            "assessed_at": ASSESS.isoformat(),
            "sample_references": [
                {
                    "sample_id": sample().sample_id,
                    "assessment_mode": "live",
                    "replay_acquired_at": ASSESS.isoformat(),
                }
            ],
        }
        assert client.post(URL, json=request).status_code == 422
