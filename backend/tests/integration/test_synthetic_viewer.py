"""Actual SELECT-only local synthetic viewer checks; no seed/data writes."""

import os

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.application.authorized_records import StorageUnavailable
from app.final_main import create_app as create_final_app
from app.main import create_app as create_default_app
from app.schemas.observation import Observation
from app.seeded_main import create_app
from app.storage.synthetic_viewer import EXPECTED_COUNTS, MISSIONS, SyntheticViewer

DSN = "host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local user=careyonda_synthetic_viewer"


@pytest.fixture
def viewer() -> SyntheticViewer:
    if os.environ.get("CAREYONDA_RUN_SYNTHETIC_VIEWER_TESTS") != "1":
        pytest.skip("explicit local SELECT-only viewer test opt-in required")
    return SyntheticViewer(DSN)


@pytest.fixture
def enabled(monkeypatch: MonkeyPatch, viewer: SyntheticViewer) -> None:
    monkeypatch.setenv("CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER", "1")
    monkeypatch.setenv("CAREYONDA_SYNTHETIC_DB_URL", DSN)


def test_actual_counts_and_all_paginated_observations(viewer: SyntheticViewer) -> None:
    catalog = viewer.catalog()
    assert catalog.table_counts == EXPECTED_COUNTS and catalog.total_seed_rows == 2852
    seen = set()
    for mission in MISSIONS:
        rows: list[Observation] = []
        for offset in range(0, 700, 100):
            page = viewer.page(mission, 100, offset)
            assert page.total == 666
            assert len(page.items) == min(100, 666 - offset)
            rows.extend(page.items)
        assert len(rows) == 666
        assert tuple(rows) == tuple(
            sorted(rows, key=lambda o: (o.timestamp, o.observation_id))
        )
        for o in rows:
            assert o.observation_id not in seen
            seen.add(o.observation_id)
            assert o.scope.mission_id == mission
            assert (
                o.provenance.origin == "simulated"
                and o.provenance.simulation
                and o.provenance.simulation.seed == 42
            )
            assert o.ingested_at is not None and o.ingested_at >= o.timestamp
    assert len(seen) == 1332


def test_scope_and_missingness(viewer: SyntheticViewer) -> None:
    first = viewer.page(MISSIONS[0], 100, 0)
    second = viewer.page(MISSIONS[1], 100, 0)
    assert first.missing + second.missing == 104
    assert first.suspect + second.suspect == 72
    wrong = viewer.page(MISSIONS[1], 100, 0, source_id="synthetic-demo-v1-simulator-c0")
    assert wrong.total == 0 and not wrong.items
    co2 = viewer.page(
        MISSIONS[0],
        100,
        0,
        "cabin_co2_partial_pressure",
        "synthetic-demo-v1-simulator-c0",
    )
    assert co2.items
    assert all(
        o.measurement.unit == "Pa" for o in co2.items if o.measurement.kind == "numeric"
    )


def test_real_permissions_and_rls(viewer: SyntheticViewer) -> None:
    viewer.verify_identity()
    assert (
        viewer.read("SELECT to_jsonb(row_security_active('public.observations'));")
        is True
    )
    assert (
        viewer.read("SELECT to_jsonb(current_setting('transaction_read_only'));")
        == "on"
    )
    # Disabling transaction read-only does not grant table write privileges.
    for sql in [
        "SET default_transaction_read_only=off; INSERT INTO public.missions(mission_id) VALUES ('must-never-insert');",
        "SELECT count(*) FROM auth.users;",
        "SELECT count(*) FROM public.profiles;",
        "SET ROLE darknight90;",
    ]:
        with pytest.raises(StorageUnavailable):
            viewer.repository.query(sql)


def test_api_actual_queries_and_authenticated_separation(enabled: None) -> None:
    with TestClient(
        create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 5000)
    ) as client:
        c = client.get("/api/v1/local-synthetic/catalog")
        assert c.status_code == 200 and c.json()["total_seed_rows"] == 2852
        page = client.get(
            "/api/v1/local-synthetic/observations",
            params={"mission_id": MISSIONS[0], "limit": 7, "offset": 7},
        )
        assert (
            page.status_code == 200
            and len(page.json()["items"]) == 7
            and page.json()["total"] == 666
        )
        assert page.json()["source"] == "synthetic_database"
        assert client.get("/api/v1/account/me").status_code == 503
        assert (
            client.post("/api/v1/local-synthetic/catalog", json={}).status_code == 405
        )
        for params in [
            {"mission_id": MISSIONS[0], "limit": 101},
            {"mission_id": "unknown-mission"},
            {"mission_id": MISSIONS[0], "offset": 2001},
            {"mission_id": MISSIONS[0], "metric": "x;drop"},
        ]:
            assert (
                client.get(
                    "/api/v1/local-synthetic/observations", params=params
                ).status_code
                == 422
            )
        assert "no-store" in page.headers.get("Cache-Control", "")


def test_disabled_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER", raising=False)
    with TestClient(
        create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 5000)
    ) as client:
        assert client.get("/api/v1/local-synthetic/catalog").status_code == 503
        assert client.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize("factory", [create_final_app, create_default_app])
def test_normal_factories_cannot_enable_viewer(
    factory: object, monkeypatch: MonkeyPatch
) -> None:
    from collections.abc import Callable
    from typing import cast

    from fastapi import FastAPI

    monkeypatch.setenv("CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER", "1")
    monkeypatch.setenv("CAREYONDA_SYNTHETIC_DB_URL", DSN)
    with TestClient(
        cast(Callable[[], FastAPI], factory)(), base_url="http://127.0.0.1"
    ) as client:
        assert client.get("/api/v1/local-synthetic/catalog").status_code == 404


def test_nonlocal_and_forwarded_rejected(enabled: None) -> None:
    with TestClient(
        create_app(), base_url="http://127.0.0.1", client=("203.0.113.1", 5000)
    ) as client:
        assert client.get("/api/v1/local-synthetic/catalog").status_code == 403
    with TestClient(
        create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 5000)
    ) as client:
        for header in ("Forwarded", "X-Forwarded-For", "X-Real-IP", "X-Forwarded-Host"):
            assert (
                client.get(
                    "/api/v1/local-synthetic/catalog",
                    headers={header: "private-value-not-reflected"},
                ).status_code
                == 403
            )
        assert (
            client.get(
                "/api/v1/local-synthetic/catalog", headers={"Host": "external.invalid"}
            ).status_code
            == 400
        )
        assert (
            client.get(
                "/api/v1/local-synthetic/catalog",
                headers={"Origin": "https://external.invalid"},
            ).status_code
            == 403
        )


def test_wrong_role_rejected_and_sanitized(monkeypatch: MonkeyPatch) -> None:
    with pytest.raises(ValueError):
        SyntheticViewer(
            "host=/tmp/careyonda-seeding-socket port=55438 dbname=careyonda_demo_seed_local user=darknight90"
        )
    monkeypatch.setenv("CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER", "1")
    monkeypatch.setenv(
        "CAREYONDA_SYNTHETIC_DB_URL",
        "postgresql://private-user:private-password@private.invalid/db",
    )
    with TestClient(
        create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 5000)
    ) as client:
        response = client.get("/api/v1/local-synthetic/catalog")
        assert response.status_code == 503
        assert "private-" not in response.text
        assert "/tmp/" not in response.text
