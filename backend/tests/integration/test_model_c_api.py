"""HTTP checks for the Model C local-entry route (SYNTHETIC values only).

Skipped, never reported as passing, when FastAPI is not installed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from app.model_c_main import create_app  # noqa: E402

NOW = datetime(2030, 3, 18, tzinfo=UTC)
HEADERS = {"Origin": "http://127.0.0.1:5173"}


def payload(days: int = 17) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "participant_id": "pseudo-api-1",
        "assessment_days": 3,
        "entries": [
            {"date": f"2030-03-{d:02d}", "sleep_duration_hours": 7.0 + (d % 3) / 10}
            for d in range(1, days + 1)
        ],
    }


def client() -> TestClient:
    return TestClient(create_app(clock=lambda: NOW), base_url="http://127.0.0.1")


def test_local_assessment_round_trip_declares_no_persistence() -> None:
    response = client().post(
        "/api/v1/model-c/local-assessments", json=payload(), headers=HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert body["persistence"] == "none"
    assert body["source"] == "transient_local_self_report"
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]
    assert body["result"]["model_version"] == "1.1.0"
    assert response.headers["Cache-Control"] == "no-store"


def test_future_entry_returns_safe_error_code_without_values() -> None:
    data = payload()
    data["entries"].append({"date": "2030-03-25", "sleep_duration_hours": 6.5})
    response = client().post(
        "/api/v1/model-c/local-assessments", json=data, headers=HEADERS
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "entry_after_report_time"
    assert "6.5" not in response.text


def test_invalid_field_is_rejected_generically() -> None:
    data = payload()
    data["entries"][0]["mood"] = "low"
    response = client().post(
        "/api/v1/model-c/local-assessments", json=data, headers=HEADERS
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_base_app_does_not_expose_the_route() -> None:
    from app.main import create_app as create_base_app

    response = TestClient(create_base_app(), base_url="http://127.0.0.1").post(
        "/api/v1/model-c/local-assessments", json=payload(), headers=HEADERS
    )
    assert response.status_code in (404, 405)
