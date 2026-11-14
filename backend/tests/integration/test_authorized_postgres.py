"""Real disposable PostgreSQL tests; identity substitution exists only in tests."""

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.application.authorized_records import AccessDenied, AuthorizedRecords
from app.final_main import create_app
from app.schemas.observation import Observation
from app.storage.authorized_postgres import PsqlRepository

ADMIN = UUID("11111111-1111-4111-8111-111111111111")
DOCTOR = UUID("22222222-2222-4222-8222-222222222222")
CREW = UUID("33333333-3333-4333-8333-333333333333")
OTHER = UUID("44444444-4444-4444-8444-444444444444")


class TestIdentity:
    __test__ = False

    def verify(self, token: str) -> UUID:
        ids = {"admin": ADMIN, "doctor": DOCTOR, "crew": CREW, "other": OTHER}
        if token not in ids:
            raise AccessDenied
        return ids[token]


@pytest.fixture
def repository() -> PsqlRepository:
    url = os.environ.get("CAREYONDA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires a separately created disposable database")
    r = PsqlRepository(url)
    r.query("""INSERT INTO auth.users(id) VALUES
      ('11111111-1111-4111-8111-111111111111'),('22222222-2222-4222-8222-222222222222'),
      ('33333333-3333-4333-8333-333333333333'),('44444444-4444-4444-8444-444444444444') ON CONFLICT DO NOTHING;
      INSERT INTO public.profiles(id) SELECT id FROM auth.users ON CONFLICT DO NOTHING;
      INSERT INTO public.user_roles(user_id,role,assigned_by_user_id,assigned_at)
        SELECT id, CASE id::text WHEN '11111111-1111-4111-8111-111111111111' THEN 'Admin'
          WHEN '22222222-2222-4222-8222-222222222222' THEN 'Doctor' ELSE 'Astronaut' END,
          '11111111-1111-4111-8111-111111111111',now()-interval '60 days'
        FROM auth.users ON CONFLICT DO NOTHING;
      INSERT INTO public.missions(mission_id) VALUES ('synthetic-db-mission'),('unrelated-db-mission') ON CONFLICT DO NOTHING;
      INSERT INTO public.astronaut_profiles(astronaut_id,user_id) VALUES
        ('synthetic-crew','33333333-3333-4333-8333-333333333333'),
        ('synthetic-other','44444444-4444-4444-8444-444444444444') ON CONFLICT DO NOTHING;
      INSERT INTO public.doctor_profiles(doctor_id,user_id) VALUES
        ('synthetic-doctor','22222222-2222-4222-8222-222222222222') ON CONFLICT DO NOTHING;
      INSERT INTO public.mission_crew_assignments(mission_id,astronaut_id,starts_at,assigned_by_user_id)
        VALUES ('synthetic-db-mission','synthetic-crew',now()-interval '30 days','11111111-1111-4111-8111-111111111111'),
        ('unrelated-db-mission','synthetic-other',now()-interval '30 days','11111111-1111-4111-8111-111111111111') ON CONFLICT DO NOTHING;
      INSERT INTO public.doctor_astronaut_assignments(doctor_id,astronaut_id,starts_at,assigned_by_user_id)
        VALUES ('synthetic-doctor','synthetic-crew',now()-interval '30 days','11111111-1111-4111-8111-111111111111') ON CONFLICT DO NOTHING;
    """)
    return r


@pytest.fixture
def observation() -> Observation:
    now = datetime.now(UTC)
    return Observation.model_validate(
        {
            "schema_version": "1.0.0",
            "observation_id": "explicitly-synthetic-db-test",
            "timestamp": now - timedelta(minutes=2),
            "ingested_at": now - timedelta(minutes=1),
            "domain": "behavioral",
            "metric": "sleep_duration",
            "scope": {
                "kind": "astronaut",
                "mission_id": "synthetic-db-mission",
                "astronaut_id": "synthetic-crew",
            },
            "measurement": {"kind": "numeric", "value": 7.0, "unit": "h"},
            "quality": {"status": "valid"},
            "provenance": {
                "source_type": "crew_report",
                "source_id": "synthetic-test-only",
                "method": "synthetic-test-entry",
                "origin": "self_reported",
            },
        }
    )


@pytest.mark.parametrize(
    "token,allowed",
    [
        ("admin", True),
        ("doctor", True),
        ("crew", True),
        ("other", False),
        ("forged", False),
    ],
)
def test_roles_read_write(
    repository: PsqlRepository, observation: Observation, token: str, allowed: bool
) -> None:
    service = AuthorizedRecords(TestIdentity(), repository)
    with TestClient(create_app(service), base_url="http://127.0.0.1") as client:
        h = {"Authorization": "Bearer " + token}
        response = client.post(
            "/api/v1/account/observations",
            json=observation.model_dump(mode="json"),
            headers=h,
        )
        assert response.status_code == (201 if allowed else 403)
        response = client.get(
            "/api/v1/account/observations?mission_id=synthetic-db-mission&astronaut_id=synthetic-crew",
            headers=h,
        )
        assert response.status_code == (200 if allowed else 403)
        if allowed:
            assert Observation.model_validate(response.json()[-1]) == observation


@pytest.mark.parametrize("token", ["admin", "doctor", "crew"])
def test_cross_mission_rejected(repository: PsqlRepository, token: str) -> None:
    service = AuthorizedRecords(TestIdentity(), repository)
    with TestClient(create_app(service), base_url="http://127.0.0.1") as client:
        response = client.get(
            "/api/v1/account/observations?mission_id=unrelated-db-mission&astronaut_id=synthetic-crew",
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == 403


@pytest.mark.parametrize(
    "token,status", [("admin", 201), ("doctor", 403), ("crew", 403)]
)
def test_admin_boundary(repository: PsqlRepository, token: str, status: int) -> None:
    from uuid import uuid4

    with TestClient(
        create_app(AuthorizedRecords(TestIdentity(), repository)),
        base_url="http://127.0.0.1",
    ) as client:
        assert (
            client.post(
                "/api/v1/account/missions",
                json={"mission_id": "synthetic-" + uuid4().hex},
                headers={"Authorization": "Bearer " + token},
            ).status_code
            == status
        )


def test_unconfigured_and_missing_identity(repository: PsqlRepository) -> None:
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/account/me").status_code == 503
    with TestClient(
        create_app(AuthorizedRecords(TestIdentity(), repository)),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.get("/api/v1/account/me").status_code == 401
        assert (
            client.get(
                "/api/v1/account/me", headers={"Authorization": "Bearer forged"}
            ).status_code
            == 403
        )


def test_atomic_write_failure(
    repository: PsqlRepository, observation: Observation
) -> None:
    from app.application.authorized_records import StorageUnavailable

    # The existing FK must reject a missing mission and roll back the root row.
    bad = observation.model_copy(
        update={
            "observation_id": "atomic-rejected",
            "scope": observation.scope.model_copy(
                update={"mission_id": "does-not-exist"}
            ),
        }
    )
    with pytest.raises(StorageUnavailable):
        repository.save(bad)
    assert (
        repository.query(
            "SELECT count(*) FROM public.observations WHERE observation_id='atomic-rejected';"
        )
        == 0
    )


def test_future_evidence_rejected(
    repository: PsqlRepository, observation: Observation
) -> None:
    service = AuthorizedRecords(TestIdentity(), repository)
    p = service.authenticate("crew")
    with pytest.raises(AccessDenied):
        service.write(p, observation, observation.timestamp - timedelta(seconds=1))


def test_suspended_identity(repository: PsqlRepository) -> None:
    repository.query(
        "UPDATE public.profiles SET status='suspended' WHERE id='44444444-4444-4444-8444-444444444444';"
    )
    try:
        with pytest.raises(AccessDenied):
            AuthorizedRecords(TestIdentity(), repository).authenticate("other")
    finally:
        repository.query(
            "UPDATE public.profiles SET status='active' WHERE id='44444444-4444-4444-8444-444444444444';"
        )


def test_astronaut_cannot_impersonate_sensor(
    repository: PsqlRepository, observation: Observation
) -> None:
    measured = Observation.model_validate(
        {
            **observation.model_dump(),
            "provenance": {
                "source_type": "sensor",
                "source_id": "synthetic-sensor-test",
                "method": "synthetic-sensor-test",
                "origin": "measured",
            },
        }
    )
    service = AuthorizedRecords(TestIdentity(), repository)
    with pytest.raises(AccessDenied):
        service.write(service.authenticate("crew"), measured, datetime.now(UTC))
