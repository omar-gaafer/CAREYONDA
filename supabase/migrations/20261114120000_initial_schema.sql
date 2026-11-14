BEGIN;

CREATE TABLE public.profiles (
    id uuid PRIMARY KEY
        REFERENCES auth.users (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.user_roles (
    grant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    role text NOT NULL CHECK (role IN ('Admin', 'Doctor', 'Astronaut')),
    assigned_by_user_id uuid NOT NULL
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    CHECK (revoked_at IS NULL OR revoked_at >= assigned_at)
);

CREATE UNIQUE INDEX user_roles_one_active_role_per_user_idx
    ON public.user_roles (user_id, role)
    WHERE revoked_at IS NULL;
CREATE INDEX user_roles_assigned_by_idx
    ON public.user_roles (assigned_by_user_id);

CREATE TABLE public.astronaut_profiles (
    astronaut_id text PRIMARY KEY,
    user_id uuid UNIQUE
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.doctor_profiles (
    doctor_id text PRIMARY KEY,
    user_id uuid NOT NULL UNIQUE
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.doctor_astronaut_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id text NOT NULL
        REFERENCES public.doctor_profiles (doctor_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    astronaut_id text NOT NULL
        REFERENCES public.astronaut_profiles (astronaut_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    starts_at timestamptz NOT NULL,
    ended_at timestamptz,
    assigned_by_user_id uuid NOT NULL
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    ended_by_user_id uuid
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at > starts_at),
    CHECK ((ended_at IS NULL) = (ended_by_user_id IS NULL))
);

CREATE UNIQUE INDEX doctor_astronaut_assignments_active_pair_idx
    ON public.doctor_astronaut_assignments (doctor_id, astronaut_id)
    WHERE ended_at IS NULL;
CREATE INDEX doctor_astronaut_assignments_astronaut_history_idx
    ON public.doctor_astronaut_assignments (astronaut_id, starts_at DESC);
CREATE INDEX doctor_astronaut_assignments_assigned_by_idx
    ON public.doctor_astronaut_assignments (assigned_by_user_id);
CREATE INDEX doctor_astronaut_assignments_ended_by_idx
    ON public.doctor_astronaut_assignments (ended_by_user_id)
    WHERE ended_by_user_id IS NOT NULL;

CREATE TABLE public.missions (
    mission_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.spacecraft (
    spacecraft_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.compartments (
    spacecraft_id text NOT NULL
        REFERENCES public.spacecraft (spacecraft_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    compartment_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (spacecraft_id, compartment_id)
);

CREATE TABLE public.mission_crew_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id text NOT NULL
        REFERENCES public.missions (mission_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    astronaut_id text NOT NULL
        REFERENCES public.astronaut_profiles (astronaut_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    starts_at timestamptz NOT NULL,
    ended_at timestamptz,
    assigned_by_user_id uuid NOT NULL
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at > starts_at)
);

CREATE UNIQUE INDEX mission_crew_assignments_active_pair_idx
    ON public.mission_crew_assignments (mission_id, astronaut_id)
    WHERE ended_at IS NULL;
CREATE INDEX mission_crew_assignments_astronaut_history_idx
    ON public.mission_crew_assignments (astronaut_id, starts_at DESC);
CREATE INDEX mission_crew_assignments_mission_history_idx
    ON public.mission_crew_assignments (mission_id, starts_at DESC);
CREATE INDEX mission_crew_assignments_assigned_by_idx
    ON public.mission_crew_assignments (assigned_by_user_id);

CREATE TABLE public.mission_spacecraft_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id text NOT NULL
        REFERENCES public.missions (mission_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    spacecraft_id text NOT NULL
        REFERENCES public.spacecraft (spacecraft_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    starts_at timestamptz NOT NULL,
    ended_at timestamptz,
    assigned_by_user_id uuid NOT NULL
        REFERENCES public.profiles (id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at > starts_at)
);

CREATE UNIQUE INDEX mission_spacecraft_assignments_active_pair_idx
    ON public.mission_spacecraft_assignments (mission_id, spacecraft_id)
    WHERE ended_at IS NULL;
CREATE INDEX mission_spacecraft_assignments_spacecraft_history_idx
    ON public.mission_spacecraft_assignments (spacecraft_id, starts_at DESC);
CREATE INDEX mission_spacecraft_assignments_mission_history_idx
    ON public.mission_spacecraft_assignments (mission_id, starts_at DESC);
CREATE INDEX mission_spacecraft_assignments_assigned_by_idx
    ON public.mission_spacecraft_assignments (assigned_by_user_id);

CREATE TABLE public.metric_definitions (
    metric_id text PRIMARY KEY,
    domain text NOT NULL CHECK (domain IN (
        'physiological',
        'environmental',
        'radiation',
        'behavioral',
        'altered_gravity',
        'mission_context'
    )),
    metric_kind text NOT NULL CHECK (metric_kind IN (
        'numeric', 'boolean', 'categorical'
    )),
    canonical_unit text,
    minimum_value double precision,
    maximum_value double precision,
    UNIQUE (metric_id, metric_kind),
    UNIQUE (metric_id, domain, metric_kind),
    UNIQUE (metric_id, metric_kind, canonical_unit),
    CHECK (
        (metric_kind = 'numeric' AND canonical_unit IS NOT NULL)
        OR
        (metric_kind IN ('boolean', 'categorical') AND canonical_unit IS NULL)
    ),
    CHECK (minimum_value IS NULL OR (
        minimum_value > '-Infinity'::double precision
        AND minimum_value < 'Infinity'::double precision
    )),
    CHECK (maximum_value IS NULL OR (
        maximum_value > '-Infinity'::double precision
        AND maximum_value < 'Infinity'::double precision
    )),
    CHECK (
        minimum_value IS NULL
        OR maximum_value IS NULL
        OR minimum_value <= maximum_value
    )
);

CREATE TABLE public.metric_allowed_scopes (
    metric_id text NOT NULL
        REFERENCES public.metric_definitions (metric_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    scope_kind text NOT NULL
        CHECK (scope_kind IN ('astronaut', 'spacecraft', 'compartment', 'mission')),
    PRIMARY KEY (metric_id, scope_kind)
);

CREATE TABLE public.metric_categories (
    metric_id text NOT NULL,
    metric_kind text NOT NULL DEFAULT 'categorical'
        CHECK (metric_kind = 'categorical'),
    category text NOT NULL,
    PRIMARY KEY (metric_id, category),
    FOREIGN KEY (metric_id, metric_kind)
        REFERENCES public.metric_definitions (metric_id, metric_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

INSERT INTO public.metric_definitions
    (metric_id, domain, metric_kind, canonical_unit, minimum_value, maximum_value)
VALUES
    ('cabin_co2_concentration', 'environmental', 'numeric', 'ppm', 0, NULL),
    ('environment_temperature', 'environmental', 'numeric', 'degC', -273.15, NULL),
    ('relative_humidity', 'environmental', 'numeric', '%', 0, 100),
    ('radiation_gcr_dose_rate', 'radiation', 'numeric', 'mGy/d', 0, NULL),
    ('radiation_saa_dose_rate', 'radiation', 'numeric', 'mGy/d', 0, NULL),
    ('radiation_total_dose_rate', 'radiation', 'numeric', 'mGy/d', 0, NULL),
    ('radiation_accumulated_dose', 'radiation', 'numeric', 'mGy', 0, NULL),
    ('cabin_co2_partial_pressure', 'environmental', 'numeric', 'Pa', 0, NULL),
    ('sleep_duration', 'behavioral', 'numeric', 'h', 0, NULL),
    ('fatigue_self_report', 'behavioral', 'categorical', NULL, NULL, NULL),
    ('communication_delay', 'mission_context', 'numeric', 's', 0, NULL),
    ('heart_rate', 'physiological', 'numeric', 'bpm', 0, NULL),
    ('ambient_pressure', 'environmental', 'numeric', 'Pa', 0, NULL),
    ('absorbed_dose', 'radiation', 'numeric', 'Gy', 0, NULL),
    ('sleep_state', 'behavioral', 'categorical', NULL, NULL, NULL),
    ('gravity_magnitude', 'altered_gravity', 'numeric', 'm/s2', 0, NULL),
    ('exercise_active', 'mission_context', 'boolean', NULL, NULL, NULL);

INSERT INTO public.metric_allowed_scopes (metric_id, scope_kind)
VALUES
    ('cabin_co2_concentration', 'spacecraft'),
    ('cabin_co2_concentration', 'mission'),
    ('environment_temperature', 'spacecraft'),
    ('environment_temperature', 'mission'),
    ('relative_humidity', 'spacecraft'),
    ('relative_humidity', 'mission'),
    ('radiation_gcr_dose_rate', 'spacecraft'),
    ('radiation_saa_dose_rate', 'spacecraft'),
    ('radiation_total_dose_rate', 'spacecraft'),
    ('radiation_accumulated_dose', 'spacecraft'),
    ('cabin_co2_partial_pressure', 'spacecraft'),
    ('cabin_co2_partial_pressure', 'compartment'),
    ('sleep_duration', 'astronaut'),
    ('fatigue_self_report', 'astronaut'),
    ('communication_delay', 'spacecraft'),
    ('communication_delay', 'mission'),
    ('heart_rate', 'astronaut'),
    ('ambient_pressure', 'spacecraft'),
    ('ambient_pressure', 'compartment'),
    ('absorbed_dose', 'astronaut'),
    ('absorbed_dose', 'spacecraft'),
    ('absorbed_dose', 'compartment'),
    ('sleep_state', 'astronaut'),
    ('gravity_magnitude', 'astronaut'),
    ('gravity_magnitude', 'spacecraft'),
    ('gravity_magnitude', 'compartment'),
    ('exercise_active', 'astronaut'),
    ('exercise_active', 'mission');

INSERT INTO public.metric_categories (metric_id, category)
VALUES
    ('fatigue_self_report', 'rested'),
    ('fatigue_self_report', 'tired'),
    ('fatigue_self_report', 'very_tired'),
    ('sleep_state', 'awake'),
    ('sleep_state', 'asleep');

CREATE TABLE public.observations (
    record_id uuid PRIMARY KEY,
    observation_id text NOT NULL,
    schema_version text NOT NULL CHECK (schema_version = '1.0.0'),
    event_at timestamptz NOT NULL,
    ingested_at timestamptz,
    domain text NOT NULL,
    metric_id text NOT NULL,
    metric_kind text NOT NULL,
    measurement_kind text NOT NULL CHECK (measurement_kind IN (
        'numeric', 'boolean', 'categorical', 'unavailable'
    )),
    scope_kind text NOT NULL
        CHECK (scope_kind IN ('astronaut', 'spacecraft', 'compartment', 'mission')),
    mission_id text NOT NULL
        REFERENCES public.missions (mission_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    astronaut_id text
        REFERENCES public.astronaut_profiles (astronaut_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    spacecraft_id text
        REFERENCES public.spacecraft (spacecraft_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    compartment_id text,
    quality_status text NOT NULL CHECK (quality_status IN (
        'valid', 'suspect', 'invalid', 'missing', 'unavailable'
    )),
    sensor_confidence double precision,
    source_type text NOT NULL CHECK (source_type IN (
        'sensor', 'crew_report', 'computation', 'simulator', 'mission_log'
    )),
    source_id text NOT NULL,
    method text NOT NULL,
    origin text NOT NULL CHECK (origin IN (
        'measured', 'self_reported', 'derived', 'simulated'
    )),
    transformation_version text,
    simulation_scenario_id text,
    simulation_run_id text,
    simulation_generator_version text,
    simulation_seed bigint,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (record_id, metric_id, metric_kind, measurement_kind),
    FOREIGN KEY (metric_id, domain, metric_kind)
        REFERENCES public.metric_definitions (metric_id, domain, metric_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (metric_id, scope_kind)
        REFERENCES public.metric_allowed_scopes (metric_id, scope_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (spacecraft_id, compartment_id)
        REFERENCES public.compartments (spacecraft_id, compartment_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (ingested_at IS NULL OR ingested_at >= event_at),
    CHECK (
        sensor_confidence IS NULL
        OR (
            sensor_confidence > '-Infinity'::double precision
            AND sensor_confidence < 'Infinity'::double precision
            AND sensor_confidence BETWEEN 0 AND 1
        )
    ),
    CHECK (
        (scope_kind = 'astronaut'
            AND astronaut_id IS NOT NULL
            AND spacecraft_id IS NULL
            AND compartment_id IS NULL)
        OR
        (scope_kind = 'spacecraft'
            AND astronaut_id IS NULL
            AND spacecraft_id IS NOT NULL
            AND compartment_id IS NULL)
        OR
        (scope_kind = 'compartment'
            AND astronaut_id IS NULL
            AND spacecraft_id IS NOT NULL
            AND compartment_id IS NOT NULL)
        OR
        (scope_kind = 'mission'
            AND astronaut_id IS NULL
            AND spacecraft_id IS NULL
            AND compartment_id IS NULL)
    ),
    CHECK (
        (origin = 'derived'
            AND transformation_version IS NOT NULL
            AND btrim(transformation_version) <> '')
        OR
        (origin <> 'derived' AND transformation_version IS NULL)
    ),
    CHECK (
        (origin = 'simulated'
            AND simulation_scenario_id IS NOT NULL
            AND simulation_run_id IS NOT NULL
            AND simulation_generator_version IS NOT NULL
            AND simulation_seed IS NOT NULL
            AND simulation_seed >= 0)
        OR
        (origin <> 'simulated'
            AND simulation_scenario_id IS NULL
            AND simulation_run_id IS NULL
            AND simulation_generator_version IS NULL
            AND simulation_seed IS NULL)
    ),
    CHECK (
        (origin = 'measured' AND source_type IN ('sensor', 'mission_log'))
        OR (origin = 'self_reported' AND source_type = 'crew_report')
        OR (origin = 'derived' AND source_type = 'computation')
        OR (origin = 'simulated' AND source_type = 'simulator')
    )
);

CREATE INDEX observations_mission_event_idx
    ON public.observations (mission_id, event_at DESC);
CREATE INDEX observations_astronaut_event_idx
    ON public.observations (astronaut_id, event_at DESC)
    WHERE astronaut_id IS NOT NULL;
CREATE INDEX observations_spacecraft_event_idx
    ON public.observations (spacecraft_id, event_at DESC)
    WHERE spacecraft_id IS NOT NULL;
CREATE INDEX observations_metric_event_idx
    ON public.observations (metric_id, event_at DESC);
CREATE INDEX observations_source_identity_idx
    ON public.observations (source_type, source_id, observation_id);
CREATE INDEX observations_compartment_event_idx
    ON public.observations (spacecraft_id, compartment_id, event_at DESC)
    WHERE compartment_id IS NOT NULL;
CREATE INDEX observations_astronaut_mission_event_idx
    ON public.observations (astronaut_id, mission_id, event_at DESC)
    WHERE astronaut_id IS NOT NULL;

CREATE TABLE public.numeric_measurements (
    record_id uuid PRIMARY KEY,
    metric_id text NOT NULL,
    metric_kind text NOT NULL DEFAULT 'numeric'
        CHECK (metric_kind = 'numeric'),
    measurement_kind text NOT NULL DEFAULT 'numeric'
        CHECK (measurement_kind = 'numeric'),
    value double precision NOT NULL,
    unit text NOT NULL,
    FOREIGN KEY (record_id, metric_id, metric_kind, measurement_kind)
        REFERENCES public.observations
            (record_id, metric_id, metric_kind, measurement_kind)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    FOREIGN KEY (metric_id, metric_kind, unit)
        REFERENCES public.metric_definitions
            (metric_id, metric_kind, canonical_unit)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (
        value > '-Infinity'::double precision
        AND value < 'Infinity'::double precision
    )
);

CREATE TABLE public.boolean_measurements (
    record_id uuid PRIMARY KEY,
    metric_id text NOT NULL,
    metric_kind text NOT NULL DEFAULT 'boolean'
        CHECK (metric_kind = 'boolean'),
    measurement_kind text NOT NULL DEFAULT 'boolean'
        CHECK (measurement_kind = 'boolean'),
    value boolean NOT NULL,
    FOREIGN KEY (record_id, metric_id, metric_kind, measurement_kind)
        REFERENCES public.observations
            (record_id, metric_id, metric_kind, measurement_kind)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    FOREIGN KEY (metric_id, metric_kind)
        REFERENCES public.metric_definitions (metric_id, metric_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE TABLE public.categorical_measurements (
    record_id uuid PRIMARY KEY,
    metric_id text NOT NULL,
    metric_kind text NOT NULL DEFAULT 'categorical'
        CHECK (metric_kind = 'categorical'),
    measurement_kind text NOT NULL DEFAULT 'categorical'
        CHECK (measurement_kind = 'categorical'),
    value text NOT NULL,
    FOREIGN KEY (record_id, metric_id, metric_kind, measurement_kind)
        REFERENCES public.observations
            (record_id, metric_id, metric_kind, measurement_kind)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    FOREIGN KEY (metric_id, metric_kind)
        REFERENCES public.metric_definitions (metric_id, metric_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (metric_id, value)
        REFERENCES public.metric_categories (metric_id, category)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE TABLE public.unavailable_measurements (
    record_id uuid PRIMARY KEY,
    metric_id text NOT NULL,
    metric_kind text NOT NULL CHECK (metric_kind IN (
        'numeric', 'boolean', 'categorical'
    )),
    measurement_kind text NOT NULL DEFAULT 'unavailable'
        CHECK (measurement_kind = 'unavailable'),
    reason text NOT NULL CHECK (reason IN (
        'not_received', 'not_collected', 'sensor_offline', 'rejected'
    )),
    FOREIGN KEY (record_id, metric_id, metric_kind, measurement_kind)
        REFERENCES public.observations
            (record_id, metric_id, metric_kind, measurement_kind)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    FOREIGN KEY (metric_id, metric_kind)
        REFERENCES public.metric_definitions (metric_id, metric_kind)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX numeric_measurements_metric_idx
    ON public.numeric_measurements (metric_id, metric_kind);
CREATE INDEX boolean_measurements_metric_idx
    ON public.boolean_measurements (metric_id, metric_kind);
CREATE INDEX categorical_measurements_metric_idx
    ON public.categorical_measurements (metric_id, metric_kind);
CREATE INDEX unavailable_measurements_metric_idx
    ON public.unavailable_measurements (metric_id, metric_kind);

CREATE TABLE public.observation_quality_reasons (
    record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    reason_code text NOT NULL,
    PRIMARY KEY (record_id, reason_code)
);

CREATE TABLE public.observation_parent_references (
    child_record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    parent_record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    PRIMARY KEY (child_record_id, parent_record_id),
    CHECK (child_record_id <> parent_record_id)
);

CREATE INDEX observation_parent_references_parent_idx
    ON public.observation_parent_references (parent_record_id);

CREATE TABLE public.ingestion_batches (
    batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_sha256 char(64),
    manifest_sha256 char(64),
    schema_version text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL,
    CHECK (
        source_sha256 IS NULL OR source_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CHECK (
        manifest_sha256 IS NULL OR manifest_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE public.ingestion_source_rows (
    batch_id uuid NOT NULL
        REFERENCES public.ingestion_batches (batch_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    row_number bigint NOT NULL CHECK (row_number > 0),
    original_fields jsonb NOT NULL,
    time_interpretation text NOT NULL,
    issue_codes text[] NOT NULL DEFAULT ARRAY[]::text[],
    PRIMARY KEY (batch_id, row_number),
    CHECK (jsonb_typeof(original_fields) = 'object')
);

CREATE TABLE public.ingestion_observation_links (
    batch_id uuid NOT NULL,
    row_number bigint NOT NULL,
    record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    PRIMARY KEY (batch_id, row_number, record_id),
    FOREIGN KEY (batch_id, row_number)
        REFERENCES public.ingestion_source_rows (batch_id, row_number)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX ingestion_observation_links_record_idx
    ON public.ingestion_observation_links (record_id);

CREATE TABLE public.ai_models (
    model_id text PRIMARY KEY
);

CREATE TABLE public.model_versions (
    version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id text NOT NULL
        REFERENCES public.ai_models (model_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    model_version text NOT NULL,
    metadata_schema_version text,
    feature_schema_version text,
    artifact_sha256 char(64),
    metadata_payload jsonb,
    created_at timestamptz,
    UNIQUE (model_id, model_version),
    CHECK (
        artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE public.inference_runs (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id uuid NOT NULL
        REFERENCES public.model_versions (version_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    request_schema_version text,
    run_status text NOT NULL CHECK (run_status IN (
        'running', 'succeeded', 'failed'
    )),
    started_at timestamptz,
    completed_at timestamptz,
    idempotency_key uuid UNIQUE,
    safe_error_code text,
    CHECK (
        started_at IS NULL
        OR completed_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE INDEX inference_runs_model_version_idx
    ON public.inference_runs (model_version_id);

CREATE TABLE public.inference_input_references (
    run_id uuid NOT NULL
        REFERENCES public.inference_runs (run_id)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    input_role text NOT NULL,
    PRIMARY KEY (run_id, record_id, input_role)
);

CREATE INDEX inference_input_references_record_idx
    ON public.inference_input_references (record_id);

CREATE TABLE public.inference_results (
    result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL
        REFERENCES public.inference_runs (run_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    result_type text NOT NULL,
    schema_version text NOT NULL,
    result_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(result_payload) = 'object')
);

CREATE INDEX inference_results_run_idx
    ON public.inference_results (run_id);

CREATE TABLE public.inference_evidence (
    result_id uuid NOT NULL
        REFERENCES public.inference_results (result_id)
        ON UPDATE RESTRICT ON DELETE CASCADE,
    record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    evidence_role text NOT NULL,
    PRIMARY KEY (result_id, record_id, evidence_role)
);

CREATE INDEX inference_evidence_record_idx
    ON public.inference_evidence (record_id);

CREATE TABLE public.investigations (
    investigation_id text PRIMARY KEY,
    schema_version text NOT NULL CHECK (schema_version = '1.0.0'),
    engine_version text NOT NULL CHECK (
        engine_version = 'reference-rules-1.0.0'
    ),
    window_seconds integer NOT NULL CHECK (window_seconds > 0),
    status text NOT NULL CHECK (status IN (
        'ranked', 'ambiguous', 'insufficient_evidence', 'conflicting_evidence'
    )),
    selected_hypothesis text,
    safety_status text NOT NULL DEFAULT 'not_evaluated'
        CHECK (safety_status = 'not_evaluated'),
    result_payload jsonb NOT NULL,
    persisted_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(result_payload) = 'object')
);

CREATE TABLE public.investigation_contexts (
    investigation_id text NOT NULL
        REFERENCES public.investigations (investigation_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    context_role text NOT NULL CHECK (context_role IN ('current', 'reference')),
    sample_id text NOT NULL,
    episode_id text NOT NULL,
    mission_id text NOT NULL
        REFERENCES public.missions (mission_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    astronaut_id text NOT NULL
        REFERENCES public.astronaut_profiles (astronaut_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    spacecraft_id text NOT NULL
        REFERENCES public.spacecraft (spacecraft_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    compartment_id text NOT NULL,
    context_at timestamptz NOT NULL,
    PRIMARY KEY (investigation_id, context_role),
    FOREIGN KEY (spacecraft_id, compartment_id)
        REFERENCES public.compartments (spacecraft_id, compartment_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
);

CREATE INDEX investigation_contexts_mission_idx
    ON public.investigation_contexts (mission_id);
CREATE INDEX investigation_contexts_astronaut_idx
    ON public.investigation_contexts (astronaut_id);
CREATE INDEX investigation_contexts_spacecraft_compartment_idx
    ON public.investigation_contexts (spacecraft_id, compartment_id);

CREATE TABLE public.investigation_hypotheses (
    investigation_id text NOT NULL
        REFERENCES public.investigations (investigation_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    hypothesis_id text NOT NULL CHECK (hypothesis_id IN (
        'baseline', 'elevated_co2', 'sleep_deprivation', 'recent_exercise'
    )),
    rank integer NOT NULL CHECK (rank > 0),
    compatibility text NOT NULL CHECK (compatibility IN (
        'supported', 'partial', 'mixed', 'contradicted', 'insufficient'
    )),
    hypothesis_payload jsonb NOT NULL,
    PRIMARY KEY (investigation_id, hypothesis_id),
    CHECK (jsonb_typeof(hypothesis_payload) = 'object')
);

ALTER TABLE public.investigations
    ADD CONSTRAINT investigations_selected_hypothesis_fk
    FOREIGN KEY (investigation_id, selected_hypothesis)
    REFERENCES public.investigation_hypotheses (investigation_id, hypothesis_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE public.investigation_observation_refs (
    reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id text NOT NULL
        REFERENCES public.investigations (investigation_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    hypothesis_id text,
    record_id uuid NOT NULL
        REFERENCES public.observations (record_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    window_kind text NOT NULL CHECK (window_kind IN ('current', 'reference')),
    reference_role text NOT NULL,
    metric_id text,
    relation text,
    FOREIGN KEY (investigation_id, hypothesis_id)
        REFERENCES public.investigation_hypotheses
            (investigation_id, hypothesis_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (
        (reference_role = 'window_input' AND hypothesis_id IS NULL)
        OR
        (reference_role <> 'window_input' AND hypothesis_id IS NOT NULL)
    )
);

CREATE INDEX investigation_observation_refs_investigation_idx
    ON public.investigation_observation_refs (investigation_id, window_kind);
CREATE INDEX investigation_observation_refs_record_idx
    ON public.investigation_observation_refs (record_id);

CREATE TABLE public.audit_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id uuid
        REFERENCES public.profiles (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    event_code text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    correlation_id text,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (jsonb_typeof(details) = 'object')
);

CREATE INDEX audit_events_actor_time_idx
    ON public.audit_events (actor_user_id, occurred_at DESC)
    WHERE actor_user_id IS NOT NULL;

CREATE TABLE public.sync_operations (
    operation_id uuid PRIMARY KEY,
    submitted_by_user_id uuid
        REFERENCES public.profiles (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    origin_install_id uuid NOT NULL,
    operation_kind text NOT NULL,
    payload_sha256 char(64) NOT NULL
        CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN (
        'received', 'applied', 'conflict', 'rejected'
    )),
    received_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    outcome_code text,
    CHECK (completed_at IS NULL OR completed_at >= received_at)
);

CREATE OR REPLACE FUNCTION public.enforce_observation_integrity()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    target_record_id uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        PERFORM public.enforce_observation_integrity_for_id(OLD.record_id);
        target_record_id := NEW.record_id;
    ELSIF TG_OP = 'DELETE' THEN
        target_record_id := OLD.record_id;
    ELSE
        target_record_id := NEW.record_id;
    END IF;

    PERFORM public.enforce_observation_integrity_for_id(target_record_id);
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.enforce_observation_integrity_for_id(
    target_record_id uuid
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    parent public.observations%ROWTYPE;
    subtype_count integer;
    quality_reason_count integer;
    parent_reference_count integer;
    unavailable_reason text;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        1,
        pg_catalog.hashtext(target_record_id::text)
    );

    SELECT *
    INTO parent
    FROM public.observations
    WHERE record_id = target_record_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    SELECT
        (SELECT count(*) FROM public.numeric_measurements WHERE record_id = target_record_id)
        + (SELECT count(*) FROM public.boolean_measurements WHERE record_id = target_record_id)
        + (SELECT count(*) FROM public.categorical_measurements WHERE record_id = target_record_id)
        + (SELECT count(*) FROM public.unavailable_measurements WHERE record_id = target_record_id)
    INTO subtype_count;

    IF subtype_count <> 1 THEN
        RAISE EXCEPTION 'observation % must have exactly one measurement subtype', target_record_id
            USING ERRCODE = '23514';
    END IF;

    IF parent.measurement_kind = 'unavailable' THEN
        SELECT reason
        INTO unavailable_reason
        FROM public.unavailable_measurements
        WHERE record_id = target_record_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'observation % requires an unavailable measurement', target_record_id
                USING ERRCODE = '23514';
        END IF;

        IF (unavailable_reason = 'not_received'
                AND parent.quality_status <> 'missing')
            OR (unavailable_reason <> 'not_received'
                AND parent.quality_status <> 'unavailable') THEN
            RAISE EXCEPTION 'observation % quality status disagrees with unavailable reason', target_record_id
                USING ERRCODE = '23514';
        END IF;
    ELSE
        IF parent.measurement_kind <> parent.metric_kind THEN
            RAISE EXCEPTION 'observation % measurement kind disagrees with metric registry', target_record_id
                USING ERRCODE = '23514';
        END IF;

        IF parent.quality_status IN ('missing', 'unavailable') THEN
            RAISE EXCEPTION 'observation % has absent quality status but a present measurement', target_record_id
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF parent.quality_status IN ('missing', 'unavailable')
        AND parent.sensor_confidence IS NOT NULL THEN
        RAISE EXCEPTION 'observation % cannot assign sensor confidence to absent evidence', target_record_id
            USING ERRCODE = '23514';
    END IF;

    SELECT count(*)
    INTO quality_reason_count
    FROM public.observation_quality_reasons
    WHERE record_id = target_record_id;

    IF (parent.quality_status = 'valid' AND quality_reason_count <> 0)
        OR (parent.quality_status <> 'valid' AND quality_reason_count = 0) THEN
        RAISE EXCEPTION 'observation % has inconsistent quality reason count', target_record_id
            USING ERRCODE = '23514';
    END IF;

    SELECT count(*)
    INTO parent_reference_count
    FROM public.observation_parent_references
    WHERE child_record_id = target_record_id;

    IF (parent.origin = 'derived' AND parent_reference_count = 0)
        OR (parent.origin <> 'derived' AND parent_reference_count <> 0) THEN
        RAISE EXCEPTION 'observation % has inconsistent derivation references', target_record_id
            USING ERRCODE = '23514';
    END IF;

    RETURN;
END;
$$;

CREATE CONSTRAINT TRIGGER observations_integrity_ck
AFTER INSERT OR UPDATE ON public.observations
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE CONSTRAINT TRIGGER numeric_measurements_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.numeric_measurements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE CONSTRAINT TRIGGER boolean_measurements_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.boolean_measurements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE CONSTRAINT TRIGGER categorical_measurements_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.categorical_measurements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE CONSTRAINT TRIGGER unavailable_measurements_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.unavailable_measurements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE CONSTRAINT TRIGGER observation_quality_reasons_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.observation_quality_reasons
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_integrity();

CREATE OR REPLACE FUNCTION public.enforce_observation_parent_integrity()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    target_record_id uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        PERFORM public.enforce_observation_integrity_for_id(OLD.child_record_id);
        target_record_id := NEW.child_record_id;
    ELSIF TG_OP = 'DELETE' THEN
        target_record_id := OLD.child_record_id;
    ELSE
        target_record_id := NEW.child_record_id;
    END IF;

    PERFORM public.enforce_observation_integrity_for_id(target_record_id);
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER observation_parent_references_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.observation_parent_references
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_observation_parent_integrity();

CREATE OR REPLACE FUNCTION public.enforce_investigation_context_integrity_for_id(
    target_investigation_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    context_count integer;
    current_count integer;
    reference_count integer;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        2,
        pg_catalog.hashtext(target_investigation_id)
    );

    IF NOT EXISTS (
        SELECT 1
        FROM public.investigations
        WHERE investigation_id = target_investigation_id
    ) THEN
        RETURN;
    END IF;

    SELECT
        count(*),
        count(*) FILTER (WHERE context_role = 'current'),
        count(*) FILTER (WHERE context_role = 'reference')
    INTO context_count, current_count, reference_count
    FROM public.investigation_contexts
    WHERE investigation_id = target_investigation_id;

    IF context_count <> 2 OR current_count <> 1 OR reference_count <> 1 THEN
        RAISE EXCEPTION 'investigation % must have one current and one reference context',
            target_investigation_id
            USING ERRCODE = '23514';
    END IF;

    RETURN;
END;
$$;

CREATE OR REPLACE FUNCTION public.enforce_investigation_context_integrity()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    target_investigation_id text;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        PERFORM public.enforce_investigation_context_integrity_for_id(
            OLD.investigation_id
        );
        target_investigation_id := NEW.investigation_id;
    ELSIF TG_OP = 'DELETE' THEN
        target_investigation_id := OLD.investigation_id;
    ELSE
        target_investigation_id := NEW.investigation_id;
    END IF;

    PERFORM public.enforce_investigation_context_integrity_for_id(
        target_investigation_id
    );

    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER investigations_contexts_integrity_ck
AFTER INSERT OR UPDATE ON public.investigations
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_investigation_context_integrity();

CREATE CONSTRAINT TRIGGER investigation_contexts_integrity_ck
AFTER INSERT OR UPDATE OR DELETE ON public.investigation_contexts
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.enforce_investigation_context_integrity();

REVOKE ALL ON FUNCTION public.enforce_observation_integrity() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.enforce_observation_integrity_for_id(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.enforce_observation_parent_integrity() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.enforce_investigation_context_integrity() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.enforce_investigation_context_integrity_for_id(text) FROM PUBLIC;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.astronaut_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_astronaut_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spacecraft ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compartments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mission_crew_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mission_spacecraft_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_allowed_scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.numeric_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.boolean_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categorical_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.unavailable_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observation_quality_reasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observation_parent_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_source_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_observation_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inference_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inference_input_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inference_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inference_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_hypotheses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investigation_observation_refs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sync_operations ENABLE ROW LEVEL SECURITY;

-- No client policies are installed until identity and access rules are approved.
-- RLS therefore denies direct anon/authenticated row access by default.

COMMIT;
