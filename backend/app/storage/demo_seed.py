"""Guarded local-only seed runner. Remote Supabase activation is intentionally absent.

No Auth rows, grants, RLS policies, trained estimators or research results are created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import cast

from pydantic import BaseModel, JsonValue, TypeAdapter

from app.storage.authorized_postgres import PsqlRepository, literal
from simulator.demo_seed import REGISTRY_TABLES, SeedBundle, generate_seed

MIGRATION_SHA256 = "1ef0d939bec205860527c68d3f2cd0b5ee80cb95bd6d08c380e2d4bec5e5e4b4"


class SeedTargetRejected(ValueError):
    pass


class SchemaStatus(BaseModel):
    database: str
    tables: int
    rls: int
    policies: int
    auth_users: int


def local_repository(database_url: str) -> PsqlRepository:
    repo = PsqlRepository(database_url)
    host = repo.environment.get("PGHOST", "")
    database = repo.environment.get("PGDATABASE", "")
    if (
        not host.startswith("/tmp/")
        or not Path(host).is_dir()
        or not re.fullmatch(r"careyonda_demo_seed_[a-z0-9_]+", database)
    ):
        raise SeedTargetRejected(
            "requires an explicitly named disposable local socket database"
        )
    return repo


def sql_value(value: JsonValue) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return literal(value)
    raise ValueError("seed rows must contain scalar values")


def table_counts(repo: PsqlRepository) -> dict[str, int]:
    names = TypeAdapter(list[str]).validate_python(
        repo.query(
            "SELECT jsonb_agg(tablename ORDER BY tablename) FROM pg_tables WHERE schemaname='public';"
        )
    )
    if len(names) != 35 or any(not re.fullmatch(r"[a-z_]+", n) for n in names):
        raise SeedTargetRejected("unexpected schema")
    pairs = ",".join(f"{literal(n)},(SELECT count(*) FROM public.{n})" for n in names)
    return TypeAdapter(dict[str, int]).validate_python(
        repo.query(f"SELECT jsonb_build_object({pairs});")
    )


def verify_rows(repo: PsqlRepository, bundle: SeedBundle) -> None:
    for table, expected in bundle.tables.items():
        if not expected:
            continue
        columns = tuple(expected[0])
        projection = ",".join(f"{literal(c)},t.{c}" for c in columns)
        actual = TypeAdapter(list[dict[str, JsonValue]]).validate_python(
            repo.query(
                f"SELECT coalesce(jsonb_agg(jsonb_build_object({projection})),'[]') FROM public.{table} t;"
            )
        )

        def normalize(rows: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
            return sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))

        if normalize(actual) != normalize(expected):
            raise SeedTargetRejected("existing seed rows differ; refusing overwrite")


def apply_seed(database_url: str, bundle: SeedBundle) -> dict[str, JsonValue]:
    repo = local_repository(database_url)
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase/migrations/20261114120000_initial_schema.sql"
    )
    if hashlib.sha256(migration.read_bytes()).hexdigest() != MIGRATION_SHA256:
        raise SeedTargetRejected("reviewed migration digest mismatch")
    status = SchemaStatus.model_validate(
        repo.query("""SELECT jsonb_build_object(
        'database',current_database(),'tables',(SELECT count(*) FROM pg_tables WHERE schemaname='public'),
        'rls',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity),
        'policies',(SELECT count(*) FROM pg_policies WHERE schemaname='public'),
        'auth_users',(SELECT count(*) FROM auth.users));""")
    )
    if (
        status.database != repo.environment["PGDATABASE"]
        or status.tables != 35
        or status.rls != 35
        or status.policies != 0
        or status.auth_users != 0
    ):
        raise SeedTargetRejected(
            "local target identity, empty Auth or default-deny RLS check failed"
        )
    before = table_counts(repo)
    user_counts = {n: c for n, c in before.items() if n not in REGISTRY_TABLES}
    expected_counts = {n: len(bundle.tables.get(n, [])) for n in user_counts}
    if any(user_counts.values()):
        if user_counts != expected_counts:
            raise SeedTargetRejected("target contains unrelated or incomplete data")
        verify_rows(repo, bundle)
    # Guard the seed transaction against concurrent writers; no table is truncated.
    sql = "BEGIN; SET CONSTRAINTS ALL DEFERRED; SELECT pg_advisory_xact_lock(7162026);"
    sql += (
        "LOCK TABLE "
        + ",".join("public." + n for n in user_counts)
        + " IN SHARE ROW EXCLUSIVE MODE;"
    )
    sql += "DO $seed_guard$ BEGIN "
    for name, count in user_counts.items():
        sql += f"IF (SELECT count(*) FROM public.{name})<>{count} THEN RAISE EXCEPTION 'target changed during seed preflight'; END IF;"
    sql += "END $seed_guard$;"
    for table, rows in bundle.tables.items():
        for row in rows:
            columns = ",".join(row)
            values = ",".join(sql_value(v) for v in row.values())
            sql += f"INSERT INTO public.{table} ({columns}) VALUES ({values}) ON CONFLICT DO NOTHING;"
    sql += "COMMIT;"
    repo.query(sql)
    verify_rows(repo, bundle)
    after = table_counts(repo)
    if {n: c for n, c in after.items() if n not in REGISTRY_TABLES} != expected_counts:
        raise SeedTargetRejected("post-seed counts mismatch")
    return {
        "scope": "local_disposable_only",
        "seed": bundle.seed,
        "fixture_sha256": bundle.digest(),
        "rows_inserted": sum(after.values()) - sum(before.values()),
        "table_counts": cast(JsonValue, {n: after[n] for n in bundle.tables}),
        "auth_users_created": 0,
        "identity_dependent_assignments": "blocked_pending_genuine_auth_users",
        "canonical_model_b_status": "unassessed",
        "remote_seeding_performed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        required=True,
        help="Local socket DSN; remote targets are rejected",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--confirm-disposable", action="store_true")
    args = parser.parse_args()
    if not args.confirm_disposable:
        parser.error("explicit --confirm-disposable is required")
    result = apply_seed(args.database, generate_seed(args.seed))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
