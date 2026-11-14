-- Run after 20261114120000_initial_schema.sql in the Supabase SQL Editor.
-- This script is read-only and expects the initial migration's no-policy
-- default-deny RLS state.
DO $$
DECLARE
    expected_tables constant text[] := ARRAY[
        'profiles',
        'user_roles',
        'astronaut_profiles',
        'doctor_profiles',
        'doctor_astronaut_assignments',
        'missions',
        'spacecraft',
        'compartments',
        'mission_crew_assignments',
        'mission_spacecraft_assignments',
        'metric_definitions',
        'metric_allowed_scopes',
        'metric_categories',
        'observations',
        'numeric_measurements',
        'boolean_measurements',
        'categorical_measurements',
        'unavailable_measurements',
        'observation_quality_reasons',
        'observation_parent_references',
        'ingestion_batches',
        'ingestion_source_rows',
        'ingestion_observation_links',
        'ai_models',
        'model_versions',
        'inference_runs',
        'inference_input_references',
        'inference_results',
        'inference_evidence',
        'investigations',
        'investigation_contexts',
        'investigation_hypotheses',
        'investigation_observation_refs',
        'audit_events',
        'sync_operations'
    ];
    missing_count integer;
    fk_count integer;
    pk_count integer;
    unique_count integer;
    check_count integer;
    rls_count integer;
    policy_count integer;
    auth_fk_count integer;
    metric_count integer;
    scope_count integer;
    category_count integer;
BEGIN
    SELECT count(*)
    INTO missing_count
    FROM unnest(expected_tables) AS expected(table_name)
    LEFT JOIN pg_catalog.pg_namespace AS n
        ON n.nspname = 'public'
    LEFT JOIN pg_catalog.pg_class AS c
        ON c.relnamespace = n.oid
        AND c.relname = expected.table_name
    WHERE c.oid IS NULL OR n.oid IS NULL OR c.relkind <> 'r';

    IF missing_count <> 0 THEN
        RAISE EXCEPTION 'initial schema verification failed: % expected public tables are missing',
            missing_count;
    END IF;

    SELECT count(*)
    INTO fk_count
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'public'
      AND rel.relname = ANY(expected_tables)
      AND con.contype = 'f';

    IF fk_count <> 58 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected 58 foreign keys, found %',
            fk_count;
    END IF;

    SELECT count(*)
    INTO pk_count
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'public'
      AND rel.relname = ANY(expected_tables)
      AND con.contype = 'p';

    IF pk_count <> 35 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected 35 primary keys, found %',
            pk_count;
    END IF;

    SELECT count(*)
    INTO unique_count
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'public'
      AND rel.relname = ANY(expected_tables)
      AND con.contype = 'u';

    IF unique_count <> 5 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected 5 unique constraints, found %',
            unique_count;
    END IF;

    SELECT count(*)
    INTO check_count
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname = 'public'
      AND rel.relname = ANY(expected_tables)
      AND con.contype = 'c';

    IF check_count <> 63 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected 63 check constraints, found %',
            check_count;
    END IF;

    SELECT count(*)
    INTO rls_count
    FROM unnest(expected_tables) AS expected(table_name)
    JOIN pg_catalog.pg_namespace AS n
        ON n.nspname = 'public'
    JOIN pg_catalog.pg_class AS c
        ON c.relnamespace = n.oid
        AND c.relname = expected.table_name
    WHERE c.relrowsecurity;

    IF rls_count <> cardinality(expected_tables) THEN
        RAISE EXCEPTION 'initial schema verification failed: RLS enabled on % of % expected tables',
            rls_count, cardinality(expected_tables);
    END IF;

    SELECT count(*)
    INTO policy_count
    FROM pg_catalog.pg_policies AS p
    WHERE p.schemaname = 'public'
      AND p.tablename = ANY(expected_tables);

    IF policy_count <> 0 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected no client RLS policies before access rules are approved; found %',
            policy_count;
    END IF;

    SELECT count(*)
    INTO auth_fk_count
    FROM pg_catalog.pg_constraint AS con
    JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
    JOIN pg_catalog.pg_class AS referenced_rel ON referenced_rel.oid = con.confrelid
    JOIN pg_catalog.pg_namespace AS referenced_ns
        ON referenced_ns.oid = referenced_rel.relnamespace
    WHERE ns.nspname = 'public'
      AND rel.relname = 'profiles'
      AND con.contype = 'f'
      AND referenced_ns.nspname = 'auth'
      AND referenced_rel.relname = 'users';

    IF auth_fk_count <> 1 THEN
        RAISE EXCEPTION 'initial schema verification failed: expected profiles.id FK to auth.users(id)';
    END IF;

    SELECT count(*) INTO metric_count FROM public.metric_definitions;
    SELECT count(*) INTO scope_count FROM public.metric_allowed_scopes;
    SELECT count(*) INTO category_count FROM public.metric_categories;

    IF metric_count <> 17 OR scope_count <> 28 OR category_count <> 5 THEN
        RAISE EXCEPTION 'initial schema verification failed: metric seed counts are %, %, %; expected 17, 28, 5',
            metric_count, scope_count, category_count;
    END IF;
END;
$$;

SELECT
    'public tables' AS check_name,
    count(*) AS actual,
    35 AS expected
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relname = ANY(ARRAY[
      'profiles', 'user_roles', 'astronaut_profiles', 'doctor_profiles',
      'doctor_astronaut_assignments', 'missions', 'spacecraft', 'compartments',
      'mission_crew_assignments', 'mission_spacecraft_assignments',
      'metric_definitions', 'metric_allowed_scopes', 'metric_categories',
      'observations', 'numeric_measurements', 'boolean_measurements',
      'categorical_measurements', 'unavailable_measurements',
      'observation_quality_reasons', 'observation_parent_references',
      'ingestion_batches', 'ingestion_source_rows',
      'ingestion_observation_links', 'ai_models', 'model_versions',
      'inference_runs', 'inference_input_references', 'inference_results',
      'inference_evidence', 'investigations', 'investigation_contexts',
      'investigation_hypotheses', 'investigation_observation_refs',
      'audit_events', 'sync_operations'
  ])
UNION ALL
SELECT
    'foreign keys',
    count(*),
    58
FROM pg_catalog.pg_constraint AS con
JOIN pg_catalog.pg_class AS rel ON rel.oid = con.conrelid
JOIN pg_catalog.pg_namespace AS ns ON ns.oid = rel.relnamespace
WHERE ns.nspname = 'public'
  AND rel.relname = ANY(ARRAY[
      'profiles', 'user_roles', 'astronaut_profiles', 'doctor_profiles',
      'doctor_astronaut_assignments', 'missions', 'spacecraft', 'compartments',
      'mission_crew_assignments', 'mission_spacecraft_assignments',
      'metric_definitions', 'metric_allowed_scopes', 'metric_categories',
      'observations', 'numeric_measurements', 'boolean_measurements',
      'categorical_measurements', 'unavailable_measurements',
      'observation_quality_reasons', 'observation_parent_references',
      'ingestion_batches', 'ingestion_source_rows',
      'ingestion_observation_links', 'ai_models', 'model_versions',
      'inference_runs', 'inference_input_references', 'inference_results',
      'inference_evidence', 'investigations', 'investigation_contexts',
      'investigation_hypotheses', 'investigation_observation_refs',
      'audit_events', 'sync_operations'
  ])
  AND con.contype = 'f'
UNION ALL
SELECT
    'RLS-enabled tables',
    count(*),
    35
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relrowsecurity
  AND c.relname = ANY(ARRAY[
      'profiles', 'user_roles', 'astronaut_profiles', 'doctor_profiles',
      'doctor_astronaut_assignments', 'missions', 'spacecraft', 'compartments',
      'mission_crew_assignments', 'mission_spacecraft_assignments',
      'metric_definitions', 'metric_allowed_scopes', 'metric_categories',
      'observations', 'numeric_measurements', 'boolean_measurements',
      'categorical_measurements', 'unavailable_measurements',
      'observation_quality_reasons', 'observation_parent_references',
      'ingestion_batches', 'ingestion_source_rows',
      'ingestion_observation_links', 'ai_models', 'model_versions',
      'inference_runs', 'inference_input_references', 'inference_results',
      'inference_evidence', 'investigations', 'investigation_contexts',
      'investigation_hypotheses', 'investigation_observation_refs',
      'audit_events', 'sync_operations'
  ])
UNION ALL
SELECT
    'client RLS policies',
    count(*),
    0
FROM pg_catalog.pg_policies AS p
WHERE p.schemaname = 'public'
  AND p.tablename = ANY(ARRAY[
      'profiles', 'user_roles', 'astronaut_profiles', 'doctor_profiles',
      'doctor_astronaut_assignments', 'missions', 'spacecraft', 'compartments',
      'mission_crew_assignments', 'mission_spacecraft_assignments',
      'metric_definitions', 'metric_allowed_scopes', 'metric_categories',
      'observations', 'numeric_measurements', 'boolean_measurements',
      'categorical_measurements', 'unavailable_measurements',
      'observation_quality_reasons', 'observation_parent_references',
      'ingestion_batches', 'ingestion_source_rows',
      'ingestion_observation_links', 'ai_models', 'model_versions',
      'inference_runs', 'inference_input_references', 'inference_results',
      'inference_evidence', 'investigations', 'investigation_contexts',
      'investigation_hypotheses', 'investigation_observation_refs',
      'audit_events', 'sync_operations'
  ]);
