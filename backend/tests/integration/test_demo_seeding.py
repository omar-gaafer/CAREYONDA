"""Opt-in disposable local seed checks. Never creates Auth identities."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.final_main import create_app
from app.storage.demo_seed import (
    SeedTargetRejected,
    apply_seed,
    local_repository,
    table_counts,
)
from simulator.demo_seed import PREFIX, generate_seed, identifier


@pytest.fixture
def seed_database() -> str:
    url = os.environ.get("CAREYONDA_SEED_TEST_DATABASE_URL")
    if not url:
        pytest.skip("explicit disposable local seed database required")
    local_repository(url)
    return url


def test_seed_twice_preserves_counts(seed_database: str) -> None:
    bundle = generate_seed()
    first = apply_seed(seed_database, bundle)
    second = apply_seed(seed_database, bundle)
    assert second["rows_inserted"] == 0
    assert first["fixture_sha256"] == second["fixture_sha256"] == bundle.digest()
    assert second["auth_users_created"] == 0
    assert second["canonical_model_b_status"] == "unassessed"


def test_schema_referential_integrity_and_no_identity_fabrication(
    seed_database: str,
) -> None:
    repo = local_repository(seed_database)
    counts = table_counts(repo)
    assert len(counts) == 35
    assert counts["observations"] == 1332
    for table in (
        "profiles",
        "user_roles",
        "doctor_profiles",
        "mission_crew_assignments",
        "doctor_astronaut_assignments",
        "investigations",
        "inference_results",
    ):
        assert counts[table] == 0
    assert repo.query("SELECT count(*) FROM auth.users;") == 0
    assert (
        repo.query(
            "SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND contype='f';"
        )
        == 58
    )
    assert (
        repo.query(
            "SELECT count(*) FROM public.observations o LEFT JOIN public.numeric_measurements n USING(record_id) WHERE o.measurement_kind='numeric' AND n.record_id IS NULL;"
        )
        == 0
    )


def test_repository_round_trip_and_mission_filter(seed_database: str) -> None:
    repo = local_repository(seed_database)
    rows = repo.observations(identifier("mission", 0), identifier("astronaut", 0))
    original = {o.observation_id: o for o in generate_seed().observations}
    assert rows
    assert all(o == original[o.observation_id] for o in rows)
    assert all(o.provenance.origin == "simulated" for o in rows)
    assert repo.observations(identifier("mission", 1), identifier("astronaut", 0)) == ()


def test_rls_remains_default_deny(seed_database: str) -> None:
    repo = local_repository(seed_database)
    # Grant SELECT only to a dedicated NOLOGIN reader; RLS is never weakened.
    assert (
        repo.query("SELECT count(*) FROM pg_policies WHERE schemaname='public';") == 0
    )
    assert (
        repo.query(
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity;"
        )
        == 35
    )
    value = repo.query(
        "GRANT USAGE ON SCHEMA public TO careyonda_seed_reader; GRANT SELECT ON ALL TABLES IN SCHEMA public TO careyonda_seed_reader; SET ROLE careyonda_seed_reader; SELECT count(*) FROM public.observations; RESET ROLE;"
    )
    assert value == 0


def test_changed_seed_and_record_collision_rejected(seed_database: str) -> None:
    repo = local_repository(seed_database)
    before = table_counts(repo)
    with pytest.raises(SeedTargetRejected):
        apply_seed(seed_database, generate_seed(43))
    rid = generate_seed().tables["numeric_measurements"][0]["record_id"]
    assert isinstance(rid, str)
    from app.storage.authorized_postgres import literal

    repo.query(
        "UPDATE public.numeric_measurements SET value=value+1 WHERE record_id="
        + literal(rid)
        + ";"
    )
    try:
        with pytest.raises(SeedTargetRejected):
            apply_seed(seed_database, generate_seed())
    finally:
        repo.query(
            "UPDATE public.numeric_measurements SET value=value-1 WHERE record_id="
            + literal(rid)
            + ";"
        )
    assert table_counts(repo) == before


def test_no_anonymous_api_or_fake_login_exposes_seed(seed_database: str) -> None:
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        assert client.get("/api/v1/account/me").status_code == 503
        assert (
            client.get(
                "/api/v1/account/observations",
                params={
                    "mission_id": identifier("mission", 0),
                    "astronaut_id": identifier("astronaut", 0),
                },
                headers={"Authorization": "Bearer invented-token"},
            ).status_code
            == 503
        )
        page = client.get("/api/v1/observations").json()
        assert not any(o["observation_id"].startswith(PREFIX) for o in page["items"])


def test_no_role_entitlements_without_auth_users(seed_database: str) -> None:
    from uuid import UUID

    from app.application.authorized_records import Principal

    repo = local_repository(seed_database)
    # Even a directly constructed role label has no entitlement without DB grants.
    for role in ("Admin", "Doctor", "Astronaut"):
        principal = Principal(
            user_id=UUID("00000000-0000-4000-8000-000000000000"), roles=(role,)
        )
        assert not repo.allowed(
            principal,
            identifier("mission", 0),
            identifier("astronaut", 0),
            datetime.now(UTC),
        )
