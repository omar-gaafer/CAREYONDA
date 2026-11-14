"""Provision only the local approved synthetic reader; never seeds or creates Auth users."""

import argparse
import hashlib
import json
import re

from pydantic import JsonValue, TypeAdapter

from app.storage.authorized_postgres import PsqlRepository, literal
from app.storage.synthetic_viewer import (
    DATABASE,
    EXPECTED_COUNTS,
    POLICY_FINGERPRINT_SQL,
    POLICY_SHA256,
    ROLE,
    SOCKET,
    TABLES,
)

EXPECTED_DIGEST = "7e7cc664f88dff71b8a51110a30dbf529206c7dafd939a9d09a62dfa4fbd93d1"


def fingerprint(repo: PsqlRepository) -> str:
    tables: dict[str, list[dict[str, JsonValue]]] = {}
    for table in TABLES:
        if table in ("missions", "spacecraft", "compartments", "astronaut_profiles"):
            sort = {
                "missions": "mission_id",
                "spacecraft": "spacecraft_id",
                "compartments": "spacecraft_id,compartment_id",
                "astronaut_profiles": "astronaut_id",
            }[table]
            sql = f"SELECT jsonb_agg(to_jsonb(t)-'created_at' ORDER BY {sort}) FROM public.{table} t;"
        elif table == "observations":
            sql = "SELECT jsonb_agg(to_jsonb(t)-'created_at'-'transformation_version' ORDER BY event_at,observation_id) FROM public.observations t;"
        else:
            remove = "-'measurement_kind'"
            if table != "unavailable_measurements":
                remove += "-'metric_kind'"
            sql = f"SELECT jsonb_agg(to_jsonb(t){remove} ORDER BY o.event_at,o.observation_id) FROM public.{table} t JOIN public.observations o USING(record_id);"
        rows = TypeAdapter(list[dict[str, JsonValue]]).validate_python(repo.query(sql))
        if table == "numeric_measurements":
            for row in rows:
                value = row["value"]
                assert isinstance(value, (float, int))
                row["value"] = float(value)
        tables[table] = rows
    return hashlib.sha256(
        json.dumps(
            tables, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def configure(database_url: str) -> dict[str, JsonValue]:
    repo = PsqlRepository(database_url)
    e = repo.environment
    if (
        e.get("PGHOST") != SOCKET
        or e.get("PGPORT") != "55438"
        or e.get("PGDATABASE") != DATABASE
    ):
        raise ValueError("only the approved disposable local database is supported")
    if repo.query("SELECT count(*) FROM auth.users;") != 0:
        raise ValueError("Auth-populated target rejected")
    if fingerprint(repo) != EXPECTED_DIGEST:
        raise ValueError("existing 2852-row seed fingerprint mismatch; no changes made")
    counts = TypeAdapter(dict[str, int]).validate_python(
        repo.query(
            "SELECT jsonb_build_object("
            + ",".join(
                f"{literal(t)},(SELECT count(*) FROM public.{t})" for t in TABLES
            )
            + ");"
        )
    )
    if counts != EXPECTED_COUNTS:
        raise ValueError("unexpected seeded row counts")
    policy_names = TypeAdapter(list[str]).validate_python(
        repo.query(
            "SELECT coalesce(jsonb_agg(policyname),'[]') FROM pg_policies WHERE schemaname='public';"
        )
    )
    if policy_names and (
        len(policy_names) != 10
        or set(policy_names) != {"careyonda_synthetic_viewer_select"}
    ):
        raise ValueError("unrelated RLS policies exist; no changes made")
    if policy_names and repo.query(POLICY_FINGERPRINT_SQL) != POLICY_SHA256:
        raise ValueError(
            "existing synthetic policy fingerprint mismatch; no changes made"
        )
    ids = TypeAdapter(list[str]).validate_python(
        repo.query(
            "SELECT jsonb_agg(record_id::text ORDER BY record_id) FROM public.observations;"
        )
    )
    if any(not re.fullmatch(r"[a-f0-9-]{36}", i) for i in ids):
        raise ValueError("invalid record key")
    approved = "ARRAY[" + ",".join(literal(i) + "::uuid" for i in ids) + "]"
    missions = (
        "mission_id IN ('synthetic-demo-v1-mission-00','synthetic-demo-v1-mission-01')"
    )
    ship = "spacecraft_id IN ('synthetic-demo-v1-ship-00','synthetic-demo-v1-ship-01')"
    astro = (
        "astronaut_id IN ("
        + ",".join(literal(f"synthetic-demo-v1-astronaut-{i:02d}") for i in range(6))
        + ") AND user_id IS NULL"
    )
    predicate = f"record_id=ANY({approved}) AND origin='simulated' AND source_type='simulator' AND method='synthetic_demo_fixture' AND simulation_seed=42 AND simulation_generator_version='1.0.0' AND simulation_run_id='synthetic-demo-v1-seed-42' AND {missions}"
    sql = f"""BEGIN;
      DO $reader$ BEGIN
        IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='{ROLE}') THEN
          CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
        END IF;
        IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='{ROLE}' AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit OR rolbypassrls))
          OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='{ROLE}')) THEN
          RAISE EXCEPTION 'existing role is not isolated';
        END IF;
      END $reader$;
      ALTER ROLE {ROLE} SET default_transaction_read_only=on;
      GRANT CONNECT ON DATABASE {DATABASE} TO {ROLE};
      GRANT USAGE ON SCHEMA public TO {ROLE};
    """
    for table in TABLES:
        if table == "missions":
            condition = missions
        elif table == "spacecraft":
            condition = ship
        elif table == "compartments":
            condition = ship + " AND compartment_id='synthetic-cabin'"
        elif table == "astronaut_profiles":
            condition = astro
        elif table == "observations":
            condition = predicate
        else:
            condition = f"EXISTS(SELECT 1 FROM public.observations o WHERE o.record_id={table}.record_id)"
        if not policy_names:
            sql += f"CREATE POLICY careyonda_synthetic_viewer_select ON public.{table} FOR SELECT TO {ROLE} USING ({condition});"
        sql += f"GRANT SELECT ON public.{table} TO {ROLE};"
    repo.query(sql + "COMMIT;")
    if fingerprint(repo) != EXPECTED_DIGEST:
        raise ValueError("unexpected dataset change")
    return {
        "local_only": True,
        "approved_seed_rows": sum(counts.values()),
        "approved_observations": len(ids),
        "dataset_sha256": EXPECTED_DIGEST,
        "reader_role": ROLE,
        "select_policies": 10,
        "data_rows_modified": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--confirm-approved-synthetic", action="store_true")
    args = parser.parse_args()
    if not args.confirm_approved_synthetic:
        parser.error("explicit synthetic target confirmation required")
    print(json.dumps(configure(args.database), indent=2))


if __name__ == "__main__":
    main()
