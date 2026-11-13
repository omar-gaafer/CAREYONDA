"""Offline local transport tests using synthetic configured evidence only."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.hazard_reasoning import investigate
from app.api.contracts import ContextsResponse, InvestigationResponse, ObservationPage
from app.api.security import MAX_BODY_BYTES
from app.main import create_app
from app.storage.local_evidence import LocalSyntheticSource


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(), base_url="http://127.0.0.1") as connection:
        yield connection


def test_health_capabilities_and_correlation(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["source"] == "configured_synthetic"
    assert len(response.headers["x-correlation-id"]) == 32
    assert response.headers["cache-control"] == "no-store"
    caps = client.get("/api/v1/capabilities").json()
    assert caps["authentication"] == "none_local_only"
    assert {c["availability"] for c in caps["capabilities"]} == {
        "available",
        "simulation_only",
        "not_implemented",
    }
    assert all(c["medically_validated"] is False for c in caps["capabilities"])


def test_observation_pagination_filters_and_provenance(client: TestClient) -> None:
    first = ObservationPage.model_validate(
        client.get("/api/v1/observations?limit=1").json()
    )
    assert first.total == 145 and len(first.items) == 1
    detail = client.get(f"/api/v1/observations/{first.items[0].observation_id}")
    assert detail.json() == first.items[0].model_dump(mode="json")
    assert detail.json()["provenance"]["origin"] == "simulated"
    page = ObservationPage.model_validate(
        client.get(
            "/api/v1/observations",
            params={
                "astronaut_id": "crew-02",
                "metric": "heart_rate",
                "start": "2026-11-13T11:50:00Z",
                "end": "2026-11-13T11:55:00Z",
            },
        ).json()
    )
    assert len(page.items) == 3
    assert all(
        o.scope.kind == "astronaut" and o.scope.astronaut_id == "crew-02"
        for o in page.items
    )
    assert client.get("/api/v1/observations?offset=9999").json()["items"] == []
    assert (
        client.get("/api/v1/observations?metric=cabin_co2_concentration").json()[
            "total"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "offset=10001",
        "metric=bad/metric",
        "metric=unknown",
        "start=2026-11-13T12:00:00",
        "start=2026-11-14T00:00:00Z&end=2026-11-13T00:00:00Z",
    ],
)
def test_invalid_queries_are_sanitized(client: TestClient, query: str) -> None:
    response = client.get("/api/v1/observations?" + query)
    assert response.status_code == 422
    assert set(response.json()) == {"api_version", "error"}
    assert (
        response.json()["error"]["correlation_id"]
        == response.headers["x-correlation-id"]
    )


def test_context_allowlist_and_unknown_evidence(client: TestClient) -> None:
    assert client.get("/api/v1/observations?astronaut_id=unknown").status_code == 403
    assert client.get("/api/v1/observations?mission_id=private").status_code == 403
    assert client.get("/api/v1/observations/unknown-id").status_code == 404
    assert client.get("/api/v1/observations/bad%20id").status_code == 422


def test_m2_outputs_exactly_match_engine_and_preserve_abstention(
    client: TestClient,
) -> None:
    contexts = ContextsResponse.model_validate(client.get("/api/v1/contexts").json())
    source = LocalSyntheticSource(
        Path(__file__).parents[2] / "app/storage/fixtures/api_evidence.json"
    )
    statuses = []
    for preset, record in zip(contexts.presets, source.presets(), strict=True):
        payload = {
            "schema_version": "1.0.0",
            "current": preset.current.model_dump(mode="json"),
            "reference": preset.reference.model_dump(mode="json"),
            "window_seconds": 300,
        }
        response = client.post("/api/v1/investigations", json=payload)
        assert response.status_code == 200
        output = InvestigationResponse.model_validate(response.json()).result
        expected = investigate(
            record.observations, record.current, record.observations, record.reference
        )
        assert output == expected
        assert output.safety_status == "not_evaluated"
        statuses.append(output.status)
    assert statuses == [
        "ranked",
        "insufficient_evidence",
        "ambiguous",
        "conflicting_evidence",
    ]
    assert client.get("/api/v1/investigations/anything").status_code == 404


@pytest.mark.parametrize("change", ["version", "subject", "window", "extra", "naive"])
def test_invalid_investigation(client: TestClient, change: str) -> None:
    preset = client.get("/api/v1/contexts").json()["presets"][0]
    body = {
        "schema_version": "1.0.0",
        "current": preset["current"],
        "reference": preset["reference"],
        "window_seconds": 300,
    }
    if change == "version":
        body["schema_version"] = "9.0.0"
    if change == "subject":
        preset["current"]["astronaut_id"] = "unauthorized"
    if change == "window":
        body["window_seconds"] = 3600
    if change == "extra":
        body["observations"] = "sensitive-request-value"
    if change == "naive":
        preset["current"]["timestamp"] = "2026-11-13T11:55:00"
    response = client.post("/api/v1/investigations", json=body)
    assert response.status_code in (403, 422)
    assert "sensitive-request-value" not in response.text


def test_request_boundaries_and_origins(client: TestClient) -> None:
    preset = client.get("/api/v1/contexts").json()["presets"][0]
    import json

    body = json.dumps(
        {
            "schema_version": "1.0.0",
            "current": preset["current"],
            "reference": preset["reference"],
        }
    )
    exact = body + " " * (MAX_BODY_BYTES - len(body.encode()))
    assert (
        client.post(
            "/api/v1/investigations",
            content=exact,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/investigations",
            content=exact + " ",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/v1/investigations",
            content=iter([b"x" * 9000, b"x" * 9000]),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/v1/investigations",
            content="private-record",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.post("/api/v1/investigations", content="text").status_code == 415
    assert (
        client.get(
            "/api/v1/health", headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/health", headers={"Host": "attacker.example"}).status_code
        == 400
    )
    allowed = client.get("/api/v1/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert client.get("/api/v1/observations?" + "x" * 2049).status_code == 414


def test_internal_failure_is_sanitized(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typing import Never

    def fail(*args: object, **kwargs: object) -> Never:
        raise RuntimeError("private-measurement-must-not-leak")

    monkeypatch.setattr("app.application.evidence.investigate", fail)
    preset = client.get("/api/v1/contexts").json()["presets"][0]
    response = client.post(
        "/api/v1/investigations",
        json={
            "schema_version": "1.0.0",
            "current": preset["current"],
            "reference": preset["reference"],
        },
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private-measurement" not in response.text


def test_telemetry_remains_disabled_despite_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FASTAPI_OTEL_AUTO_CONFIGURE", "true")
    with TestClient(create_app(), base_url="http://127.0.0.1") as connection:
        assert connection.get("/api/v1/health").status_code == 200
