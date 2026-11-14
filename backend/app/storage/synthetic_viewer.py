"""Fixed read-only queries using a non-owner, SELECT-only, RLS-restricted identity."""

from pydantic import BaseModel, TypeAdapter

from app.application.authorized_records import StorageUnavailable
from app.schemas.observation import Observation
from app.schemas.synthetic_viewer import MissionSummary, SyntheticCatalog, SyntheticPage
from app.storage.authorized_postgres import PsqlRepository, literal

POLICY_SHA256 = "08ef9c893eed94b9a2b228dbb5f359418c8a5cda5ef3250704c5bdec914bf542"
POLICY_FINGERPRINT_SQL = "SELECT to_jsonb(encode(sha256(convert_to(coalesce(string_agg(tablename||'|'||cmd||'|'||roles::text||'|'||permissive||'|'||coalesce(qual,'')||'|'||coalesce(with_check,''),E'\\n' ORDER BY tablename),''),'UTF8')),'hex')) FROM pg_policies WHERE schemaname='public';"

ROLE = "careyonda_synthetic_viewer"
DATABASE = "careyonda_demo_seed_local"
SOCKET = "/tmp/careyonda-seeding-socket"
TABLES = (
    "missions",
    "spacecraft",
    "compartments",
    "astronaut_profiles",
    "observations",
    "numeric_measurements",
    "boolean_measurements",
    "categorical_measurements",
    "unavailable_measurements",
    "observation_quality_reasons",
)
EXPECTED_COUNTS = dict(
    zip(TABLES, (2, 2, 2, 6, 1332, 803, 215, 210, 104, 176), strict=True)
)
MISSIONS = ("synthetic-demo-v1-mission-00", "synthetic-demo-v1-mission-01")


class Identity(BaseModel):
    name: str
    database: str
    privileged: bool
    writes: bool
    owns: bool
    memberships: int
    rls: int
    policies: int


class PageCounts(BaseModel):
    total: int
    missing: int
    suspect: int


class SyntheticViewer:
    def __init__(self, database_url: str) -> None:
        self.repository = PsqlRepository(database_url)
        env = self.repository.environment
        if (
            env.get("PGHOST") != SOCKET
            or env.get("PGDATABASE") != DATABASE
            or env.get("PGUSER") != ROLE
            or env.get("PGPORT") != "55438"
        ):
            raise ValueError("approved local synthetic reader configuration required")

    def read(self, sql: str) -> object:
        return self.repository.query(
            "BEGIN READ ONLY; SET LOCAL row_security=on; " + sql + " COMMIT;"
        )

    def verify_identity(self) -> None:
        if self.read(POLICY_FINGERPRINT_SQL) != POLICY_SHA256:
            raise StorageUnavailable("synthetic RLS policy fingerprint mismatch")
        status = Identity.model_validate(
            self.read("""SELECT jsonb_build_object(
          'name',current_user,'database',current_database(),
          'privileged',(SELECT rolsuper OR rolbypassrls OR rolinherit OR rolcreaterole OR rolcreatedb FROM pg_roles WHERE rolname=current_user),
          'writes',EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND has_table_privilege(current_user,quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),
          'owns',EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tableowner=current_user),
          'memberships',(SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)),
          'rls',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity),
          'policies',(SELECT count(*) FROM pg_policies WHERE schemaname='public' AND policyname='careyonda_synthetic_viewer_select' AND roles=ARRAY[current_user]::name[]));""")
        )
        if (
            status.name != ROLE
            or status.database != DATABASE
            or status.privileged
            or status.writes
            or status.owns
            or status.memberships
            or status.rls != 35
            or status.policies != 10
        ):
            raise StorageUnavailable("synthetic reader identity not permitted")

    def catalog(self) -> SyntheticCatalog:
        self.verify_identity()
        counts = TypeAdapter(dict[str, int]).validate_python(
            self.read(
                "SELECT jsonb_build_object("
                + ",".join(
                    f"{literal(n)},(SELECT count(*) FROM public.{n})" for n in TABLES
                )
                + ");"
            )
        )
        if counts != EXPECTED_COUNTS:
            raise StorageUnavailable(
                "approved synthetic dataset changed or unavailable"
            )
        missions = TypeAdapter(tuple[MissionSummary, ...]).validate_python(
            self.read("""SELECT coalesce(jsonb_agg(jsonb_build_object(
          'mission_id',m.mission_id,
          'spacecraft_ids',(SELECT coalesce(jsonb_agg(DISTINCT o.spacecraft_id),'[]') FROM public.observations o WHERE o.mission_id=m.mission_id AND o.spacecraft_id IS NOT NULL),
          'astronaut_ids',(SELECT coalesce(jsonb_agg(DISTINCT o.astronaut_id),'[]') FROM public.observations o JOIN public.astronaut_profiles a USING(astronaut_id) WHERE o.mission_id=m.mission_id),
          'source_ids',(SELECT coalesce(jsonb_agg(DISTINCT o.source_id),'[]') FROM public.observations o WHERE o.mission_id=m.mission_id),
          'association_basis','observation_scope') ORDER BY m.mission_id),'[]') FROM public.missions m;""")
        )
        return SyntheticCatalog(
            missions=missions, table_counts=counts, total_seed_rows=sum(counts.values())
        )

    def page(
        self,
        mission: str,
        limit: int,
        offset: int,
        metric: str | None = None,
        source_id: str | None = None,
    ) -> SyntheticPage:
        self.verify_identity()
        if mission not in MISSIONS or not 1 <= limit <= 100 or not 0 <= offset <= 2000:
            raise ValueError("invalid synthetic query")
        where = "o.mission_id=" + literal(mission)
        if metric:
            where += " AND o.metric_id=" + literal(metric)
        if source_id:
            where += " AND o.source_id=" + literal(source_id)
        counts = PageCounts.model_validate(
            self.read(
                f"SELECT jsonb_build_object('total',count(*),'missing',count(*) FILTER(WHERE o.quality_status='missing'),'suspect',count(*) FILTER(WHERE o.quality_status='suspect')) FROM public.observations o WHERE {where};"
            )
        )
        sql = f"""SELECT coalesce(jsonb_agg(payload ORDER BY event_at,observation_id),'[]') FROM (
          SELECT o.event_at,o.observation_id,jsonb_build_object(
            'schema_version',o.schema_version,'observation_id',o.observation_id,'timestamp',o.event_at,
            'ingested_at',o.ingested_at,'domain',o.domain,'metric',o.metric_id,
            'scope',jsonb_strip_nulls(jsonb_build_object('kind',o.scope_kind,'mission_id',o.mission_id,
              'astronaut_id',o.astronaut_id,'spacecraft_id',o.spacecraft_id,'compartment_id',o.compartment_id)),
            'measurement',CASE o.measurement_kind
              WHEN 'numeric' THEN jsonb_build_object('kind','numeric','value',n.value,'unit',n.unit)
              WHEN 'boolean' THEN jsonb_build_object('kind','boolean','value',b.value)
              WHEN 'categorical' THEN jsonb_build_object('kind','categorical','value',c.value)
              ELSE jsonb_build_object('kind','unavailable','reason',u.reason) END,
            'quality',jsonb_build_object('status',o.quality_status,'sensor_confidence',o.sensor_confidence,
               'reason_codes',(SELECT coalesce(jsonb_agg(q.reason_code ORDER BY q.reason_code),'[]') FROM public.observation_quality_reasons q WHERE q.record_id=o.record_id)),
            'provenance',jsonb_build_object('source_type',o.source_type,'source_id',o.source_id,'method',o.method,'origin',o.origin,
              'parent_observation_ids','[]'::jsonb,'transformation_version',NULL,'simulation',
              jsonb_build_object('scenario_id',o.simulation_scenario_id,'run_id',o.simulation_run_id,'generator_version',o.simulation_generator_version,'seed',o.simulation_seed))) AS payload
          FROM public.observations o
          LEFT JOIN public.numeric_measurements n USING(record_id)
          LEFT JOIN public.boolean_measurements b USING(record_id)
          LEFT JOIN public.categorical_measurements c USING(record_id)
          LEFT JOIN public.unavailable_measurements u USING(record_id)
          WHERE {where} ORDER BY o.event_at,o.observation_id LIMIT {limit} OFFSET {offset}) bounded;"""
        items = TypeAdapter(tuple[Observation, ...]).validate_python(self.read(sql))
        if any(
            o.provenance.origin != "simulated"
            or o.provenance.simulation is None
            or o.provenance.simulation.seed != 42
            or o.scope.mission_id != mission
            for o in items
        ):
            raise StorageUnavailable("synthetic provenance mismatch")
        return SyntheticPage(
            mission_id=mission,
            items=items,
            limit=limit,
            offset=offset,
            **counts.model_dump(),
        )
