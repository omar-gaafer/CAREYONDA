"""Combined demo routes use synthetic inputs, never fitted artifacts."""

from fastapi.testclient import TestClient

from app.demo_main import create_app
from app.main import create_app as create_base_app
from tests.environmental_context_fixtures import sample
from tests.integration.test_model_a_api import (
    ASSESS,
    NOW,
    configured,
    fake_loader,
)
from tests.integration.test_model_a_api import (
    payload as environmental_payload,
)
from tests.integration.test_model_c_api import NOW as C_NOW
from tests.integration.test_model_c_api import payload as local_payload


def test_default_demo_is_honest_and_model_c_runs_without_model_a() -> None:
    with TestClient(create_app(clock=lambda: C_NOW), base_url="http://127.0.0.1") as c:
        assert c.get("/api/v1/health").status_code == 200
        capabilities = {
            x["name"]: x["availability"]
            for x in c.get("/api/v1/capabilities").json()["capabilities"]
        }
        assert capabilities["trained_models"] == "unavailable"
        assert capabilities["model_c_transient_sleep_fatigue_research"] == "available"
        assert capabilities["safety_policies"] == "not_implemented"
        assert c.get("/api/v1/environmental/authorized-samples").json()["samples"] == []
        assert (
            c.post(
                "/api/v1/environmental/anomaly-context",
                json=environmental_payload(sample()),
            ).status_code
            == 503
        )
        result = c.post("/api/v1/model-c/local-assessments", json=local_payload())
        assert result.status_code == 200
        assert result.json()["source"] == "transient_local_self_report"
        assert result.json()["persistence"] == "none"
        assert result.json()["result"]["subject_id"] == "pseudo-api-1"
        assert c.post("/api/v1/model-c/local-assessments", json={}).status_code == 422


def test_configured_demo_model_a_and_m2_are_independent() -> None:
    source = sample()
    with TestClient(
        create_app(configured((source,)), model_loader=fake_loader, clock=lambda: NOW),
        base_url="http://127.0.0.1",
    ) as c:
        result = c.post(
            "/api/v1/environmental/anomaly-context",
            json={
                "schema_version": "1.1.0",
                "assessed_at": ASSESS.isoformat(),
                "sample_references": [
                    {"sample_id": source.sample_id, "assessment_mode": "live"}
                ],
            },
        )
        assert result.status_code == 200
        assert result.json()["contexts"][0]["status"] == "flagged"
        capabilities = {
            x["name"]: x["availability"]
            for x in c.get("/api/v1/capabilities").json()["capabilities"]
        }
        assert capabilities["trained_models"] == "available"
        base = TestClient(create_base_app(), base_url="http://127.0.0.1")
        for path in ("/api/v1/contexts", "/api/v1/observations"):
            assert c.get(path).json() == base.get(path).json()
        preset = c.get("/api/v1/contexts").json()["presets"][0]
        request = {
            "schema_version": "1.0.0",
            "current": preset["current"],
            "reference": preset["reference"],
        }
        assert (
            c.post("/api/v1/investigations", json=request).json()
            == base.post("/api/v1/investigations", json=request).json()
        )
