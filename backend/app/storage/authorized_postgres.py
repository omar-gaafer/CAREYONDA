"""Optional PostgreSQL adapter using the separately provisioned psql CLI.

No driver installation, import-time I/O or browser database access. Each write is
one transaction. Connection configuration is server-only and never logged.
"""

import json
import os
import shlex
import subprocess
from datetime import datetime
from urllib.parse import parse_qsl, unquote, urlparse
from uuid import UUID, uuid4

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.application.authorized_records import (
    AccessDenied,
    Principal,
    StorageUnavailable,
)
from app.schemas.observation import Observation


def literal(value: str) -> str:
    # PostgreSQL standard-conforming SQL literals; no command/shell interpolation.
    return "'" + value.replace("'", "''") + "'"


class RoleRow(BaseModel):
    role: str


class CountRow(BaseModel):
    allowed: bool


class PsqlRepository:
    def __init__(self, database_url: str) -> None:
        parsed = urlparse(database_url)
        if parsed.scheme in ("postgres", "postgresql"):
            fields = {
                "host": parsed.hostname or "",
                "port": str(parsed.port or 5432),
                "dbname": unquote(parsed.path.lstrip("/")),
                "user": unquote(parsed.username or ""),
                "password": unquote(parsed.password or ""),
            }
            fields.update(dict(parse_qsl(parsed.query)))
        else:
            fields = dict(part.split("=", 1) for part in shlex.split(database_url))
        allowed = {
            "host",
            "port",
            "dbname",
            "user",
            "password",
            "sslmode",
            "connect_timeout",
        }
        if not fields or not set(fields) <= allowed:
            raise ValueError("unsupported database connection settings")
        self.environment = {
            "PG" + ("DATABASE" if k == "dbname" else k.upper()): v
            for k, v in fields.items()
            if v
        }
        self.environment.setdefault("PGCONNECT_TIMEOUT", "5")

    def query(self, sql: str) -> object:
        env = {
            **os.environ,
            **self.environment,
            "PGOPTIONS": "-c statement_timeout=5000 -c timezone=UTC -c standard_conforming_strings=on",
        }
        try:
            result = subprocess.run(
                [
                    "/usr/bin/psql",
                    "--no-psqlrc",
                    "--quiet",
                    "--tuples-only",
                    "--no-align",
                    "--set",
                    "ON_ERROR_STOP=1",
                ],
                input=sql,
                text=True,
                capture_output=True,
                env=env,
                timeout=8,
                check=True,
            )
            lines = result.stdout.strip().splitlines()
            return json.loads(lines[-1]) if lines else None
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise StorageUnavailable("database operation unavailable") from exc

    def principal(self, user_id: UUID) -> Principal:
        rows = TypeAdapter(list[RoleRow]).validate_python(
            self.query(
                "SELECT coalesce(jsonb_agg(jsonb_build_object('role',r.role)), '[]') "
                "FROM public.user_roles r JOIN public.profiles p ON p.id=r.user_id "
                f"WHERE p.id={literal(str(user_id))}::uuid AND p.status='active' "
                "AND r.revoked_at IS NULL AND r.assigned_at<=now();"
            )
        )
        if not rows:
            raise AccessDenied
        return Principal(user_id=user_id, roles=tuple(sorted(r.role for r in rows)))

    def allowed(
        self, principal: Principal, mission: str, astronaut: str, at: datetime
    ) -> bool:
        uid, m, a, t = map(
            literal, (str(principal.user_id), mission, astronaut, at.isoformat())
        )
        # Mission membership is mandatory even for Admin; no cross-mission inference.
        query = f"""SELECT jsonb_build_object('allowed', EXISTS (
          SELECT 1 FROM public.mission_crew_assignments c
          WHERE c.mission_id={m} AND c.astronaut_id={a}
          AND c.starts_at<={t}::timestamptz AND (c.ended_at IS NULL OR c.ended_at>{t}::timestamptz)
          AND EXISTS (SELECT 1 FROM public.profiles p WHERE p.id={uid}::uuid AND p.status='active')
          AND EXISTS (SELECT 1 FROM public.user_roles r WHERE r.user_id={uid}::uuid
            AND r.revoked_at IS NULL AND r.assigned_at<=now() AND (
              r.role='Admin' OR
              (r.role='Astronaut' AND EXISTS (SELECT 1 FROM public.astronaut_profiles ap
                WHERE ap.user_id={uid}::uuid AND ap.astronaut_id={a})) OR
              (r.role='Doctor' AND EXISTS (SELECT 1 FROM public.doctor_profiles dp
                JOIN public.doctor_astronaut_assignments da ON da.doctor_id=dp.doctor_id
                WHERE dp.user_id={uid}::uuid AND da.astronaut_id={a}
                AND da.starts_at<={t}::timestamptz AND (da.ended_at IS NULL OR da.ended_at>{t}::timestamptz)))
            ))));"""
        return CountRow.model_validate(self.query(query)).allowed

    def observations(self, mission: str, astronaut: str) -> tuple[Observation, ...]:
        # A stable bounded page; no broad table or arbitrary SQL API is exposed.
        sql = f"""SELECT coalesce(jsonb_agg(payload ORDER BY event_at,record_id),'[]') FROM (
          SELECT o.event_at,o.record_id, jsonb_build_object(
            'schema_version',o.schema_version,'observation_id',o.observation_id,
            'timestamp',o.event_at,'ingested_at',o.ingested_at,'domain',o.domain,'metric',o.metric_id,
            'scope',jsonb_build_object('kind','astronaut','mission_id',o.mission_id,'astronaut_id',o.astronaut_id),
            'measurement',jsonb_build_object('kind','numeric','value',n.value,'unit',n.unit),
            'quality',jsonb_build_object('status',o.quality_status,'sensor_confidence',o.sensor_confidence,
               'reason_codes',(SELECT coalesce(jsonb_agg(q.reason_code ORDER BY q.reason_code),'[]')
                 FROM public.observation_quality_reasons q WHERE q.record_id=o.record_id)),
            'provenance',jsonb_build_object('source_type',o.source_type,'source_id',o.source_id,
               'method',o.method,'origin',o.origin,'parent_observation_ids','[]'::jsonb,
               'transformation_version',NULL,'simulation', CASE WHEN o.origin='simulated' THEN
                 jsonb_build_object('scenario_id',o.simulation_scenario_id,'run_id',o.simulation_run_id,
                   'generator_version',o.simulation_generator_version,'seed',o.simulation_seed)
                 ELSE NULL END)) AS payload
          FROM public.observations o JOIN public.numeric_measurements n USING(record_id)
          WHERE o.scope_kind='astronaut' AND o.mission_id={literal(mission)}
          AND o.astronaut_id={literal(astronaut)} AND o.origin<>'derived'
          ORDER BY o.event_at,o.record_id LIMIT 100) bounded;"""
        try:
            return TypeAdapter(tuple[Observation, ...]).validate_python(self.query(sql))
        except ValidationError as exc:
            raise StorageUnavailable("stored evidence contract mismatch") from exc

    def save(self, observation: Observation) -> None:
        o = observation
        if o.scope.kind != "astronaut" or o.measurement.kind != "numeric":
            raise AccessDenied
        rid = literal(str(uuid4()))
        sim = o.provenance.simulation
        values: dict[str, str] = {
            "record_id": rid,
            "observation_id": literal(o.observation_id),
            "schema_version": literal(o.schema_version),
            "event_at": literal(o.timestamp.isoformat()),
            "ingested_at": literal(o.ingested_at.isoformat())
            if o.ingested_at
            else "NULL",
            "domain": literal(o.domain),
            "metric_id": literal(o.metric),
            "metric_kind": "'numeric'",
            "measurement_kind": "'numeric'",
            "scope_kind": "'astronaut'",
            "mission_id": literal(o.scope.mission_id),
            "astronaut_id": literal(o.scope.astronaut_id),
            "quality_status": literal(o.quality.status),
            "sensor_confidence": str(o.quality.sensor_confidence)
            if o.quality.sensor_confidence is not None
            else "NULL",
            "source_type": literal(o.provenance.source_type),
            "source_id": literal(o.provenance.source_id),
            "method": literal(o.provenance.method),
            "origin": literal(o.provenance.origin),
            "simulation_scenario_id": literal(sim.scenario_id) if sim else "NULL",
            "simulation_run_id": literal(sim.run_id) if sim else "NULL",
            "simulation_generator_version": literal(sim.generator_version)
            if sim
            else "NULL",
            "simulation_seed": str(sim.seed) if sim else "NULL",
        }
        sql = f"BEGIN; INSERT INTO public.observations ({','.join(values)}) VALUES ({','.join(values.values())});"
        sql += f"INSERT INTO public.numeric_measurements(record_id,metric_id,value,unit) VALUES ({rid},{literal(o.metric)},{o.measurement.value},{literal(o.measurement.unit)});"
        for reason in o.quality.reason_codes:
            sql += f"INSERT INTO public.observation_quality_reasons VALUES ({rid},{literal(reason)});"
        self.query(sql + "COMMIT;")

    def create_mission(self, mission: str) -> None:
        self.query(
            f"INSERT INTO public.missions(mission_id) VALUES ({literal(mission)});"
        )
