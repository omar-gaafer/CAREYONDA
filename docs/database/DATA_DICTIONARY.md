# CAREYONDA Proposed Database Data Dictionary

This document describes a candidate PostgreSQL schema only. It is not DDL, a
migration, or a claim that the fields are already stored. `Contract` means the
field's meaning is directly present in a named source contract; `Proposed` means
the field or relational representation is a design addition. Table names,
database types, keys, nullability, and persistence are always proposed, even
when their meaning maps to a contract. Unless a row explicitly identifies a
source contract field, treat its database column as proposed. Nullability is
for the proposed cloud schema. Sensitive data is not supplied in fixtures here.

PostgreSQL types: `uuid`, `text`, `text[]`, `boolean`, `integer`, `bigint`,
`double precision`, `timestamptz`, `jsonb`, and optional validated `char(64)`
for lowercase SHA-256 digests. Enum-like values can be PostgreSQL enums or
checked `text`; migrations must not freeze an unsupported contract vocabulary.

## Identity and access

### `profiles` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `id` | `uuid` | PK; FK `auth.users(id)` | No | Auth identity UUID; external Supabase-managed reference |
| `status` | `text` | — | No | Proposed; CHECK `active`, `suspended`; account lifecycle, not in current code |
| `created_at` | `timestamptz` | — | No | Proposed server timestamp |
| `updated_at` | `timestamptz` | — | No | Proposed server timestamp; update only through authorized service |

No email, name, or health fields are copied from Auth absent an approved need.
Prefer suspension over hard deletion. The external Auth FK should restrict
deletion until retention/anonymization rules are approved.

### `user_roles` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `grant_id` | `uuid` | PK | No | Proposed immutable grant identity |
| `user_id` | `uuid` | FK `profiles.id` | No | Role recipient |
| `role` | `text` | — | No | CHECK `Admin`, `Doctor`, `Astronaut`; multiple grants per user |
| `assigned_by_user_id` | `uuid` | FK `profiles.id` | No | Authorized admin actor; server verifies actor's active grant |
| `assigned_at` | `timestamptz` | — | No | Proposed server time |
| `revoked_at` | `timestamptz` | — | Yes | Null means current grant; revocation retains history |

Unique partial index: `(user_id, role) WHERE revoked_at IS NULL`. No role is
implicitly granted at signup. First-admin bootstrap is unresolved.

### `astronaut_profiles` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `astronaut_id` | `text` | PK | No | Contract domain identifier; retain string form |
| `user_id` | `uuid` | FK `profiles.id`, UNIQUE | Yes | Proposed optional Auth association; absent for synthetic/unclaimed subjects |
| `created_at` | `timestamptz` | — | No | Proposed creation time |

The unique optional account link is a design assumption: confirm whether an
account may represent multiple astronaut subjects.

### `doctor_profiles` — required for Doctor role

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `doctor_id` | `text` | PK | No | Proposed domain identifier; no doctor ID contract currently exists |
| `user_id` | `uuid` | FK `profiles.id`, UNIQUE | No | Doctor's authenticated profile |
| `created_at` | `timestamptz` | — | No | Proposed creation time |

### `doctor_astronaut_assignments` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `assignment_id` | `uuid` | PK | No | Proposed stable assignment record |
| `doctor_id` | `text` | FK `doctor_profiles.doctor_id` | No | Assigned Doctor |
| `astronaut_id` | `text` | FK `astronaut_profiles.astronaut_id` | No | Assigned subject |
| `starts_at` | `timestamptz` | — | No | Effective start |
| `ended_at` | `timestamptz` | — | Yes | Null means active; preserve ended assignments |
| `assigned_by_user_id` | `uuid` | FK `profiles.id` | No | Granting admin actor |
| `ended_by_user_id` | `uuid` | FK `profiles.id` | Yes | Actor ending assignment |
| `created_at` | `timestamptz` | — | No | Proposed server record time |

CHECK `ended_at IS NULL OR ended_at > starts_at`; partial unique index on
`(doctor_id, astronaut_id) WHERE ended_at IS NULL`. Temporal overlap policy is
unresolved. Require `ended_by_user_id` to be null exactly while `ended_at` is
null, unless an approved closure workflow defines another actor model.

Ordinary FKs do not enforce role/profile consistency. A Doctor role grant must
match a Doctor profile, and any account granted Astronaut access must match its
linked astronaut profile; the converse must also be defined. Enforce approved
invariants atomically in trusted backend transactions and consider a deferred
database constraint trigger if other write paths exist. Admin has no role-specific
profile. Bootstrap and multi-role policy remain unresolved.

## Missions and locations

### `missions` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `mission_id` | `text` | PK | No | Contract scope identifier |
| `created_at` | `timestamptz` | — | No | Proposed catalog creation time |

No mission name, dates, status, or phase fields are verified by current contracts.

### `spacecraft` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `spacecraft_id` | `text` | PK | No | Contract scope identifier |
| `created_at` | `timestamptz` | — | No | Proposed catalog creation time |

### `compartments` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `spacecraft_id` | `text` | PK part; FK `spacecraft.spacecraft_id` | No | Owning spacecraft |
| `compartment_id` | `text` | PK part | No | Contract scope identifier within spacecraft |
| `created_at` | `timestamptz` | — | No | Proposed catalog creation time |

### `mission_crew_assignments` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `assignment_id` | `uuid` | PK | No | Proposed stable history record |
| `mission_id` | `text` | FK `missions.mission_id` | No | Mission |
| `astronaut_id` | `text` | FK `astronaut_profiles.astronaut_id` | No | Crew subject |
| `starts_at` | `timestamptz` | — | No | Effective start |
| `ended_at` | `timestamptz` | — | Yes | Null means active |
| `assigned_by_user_id` | `uuid` | FK `profiles.id` | No | Authorized actor |
| `created_at` | `timestamptz` | — | No | Proposed server record time |

CHECK `ended_at IS NULL OR ended_at > starts_at`; partial unique index on
`(mission_id, astronaut_id) WHERE ended_at IS NULL`. No end-actor column is
currently proposed; decide whether the closure actor needs a dedicated FK or a
reviewed audit event.

### `mission_spacecraft_assignments` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `assignment_id` | `uuid` | PK | No | Proposed stable history record |
| `mission_id` | `text` | FK `missions.mission_id` | No | Mission |
| `spacecraft_id` | `text` | FK `spacecraft.spacecraft_id` | No | Spacecraft |
| `starts_at` | `timestamptz` | — | No | Effective start |
| `ended_at` | `timestamptz` | — | Yes | Null means active |
| `assigned_by_user_id` | `uuid` | FK `profiles.id` | No | Authorized actor |
| `created_at` | `timestamptz` | — | No | Proposed server record time |

CHECK `ended_at IS NULL OR ended_at > starts_at`; partial unique index on
`(mission_id, spacecraft_id) WHERE ended_at IS NULL`. No end-actor column is
currently proposed; decide whether the closure actor needs a dedicated FK or a
reviewed audit event.

## Metric registry

### `metric_definitions` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `metric_id` | `text` | PK | No | Current registry metric string |
| `domain` | `text` | — | No | Observation v1 domain |
| `metric_kind` | `text` | — | No | Registry's expected value type: `numeric`, `boolean`, or `categorical` |
| `canonical_unit` | `text` | — | Yes | Registry unit; null for boolean/categorical |
| `minimum_value` | `double precision` | — | Yes | Physical-domain bound only, not a clinical threshold |
| `maximum_value` | `double precision` | — | Yes | Physical-domain bound only |

Unique keys: `(metric_id, metric_kind)`, `(metric_id, domain, metric_kind)`,
and `(metric_id, metric_kind, canonical_unit)`. CHECK bounds are ordered when
both exist. Numeric metrics require a non-null canonical unit; nonnumeric
metrics do not acquire a fabricated unit. The source contract names the expected
type `measurement_kind`; `metric_kind` is the proposed database name that
distinguishes registry expectation from an observation's actual
`measurement_kind` variant.

The following is the verified current `METRIC_REGISTRY` snapshot. It is source
contract data, not a proposal for additional metrics. Empty bounds/categories
mean the registry defines none.

| Metric ID | Domain | Registry kind | Canonical unit | Minimum | Maximum | Allowed scopes | Categories |
|---|---|---|---|---:|---:|---|---|
| `cabin_co2_concentration` | environmental | numeric | ppm | 0 | — | spacecraft, mission | — |
| `environment_temperature` | environmental | numeric | degC | -273.15 | — | spacecraft, mission | — |
| `relative_humidity` | environmental | numeric | % | 0 | 100 | spacecraft, mission | — |
| `radiation_gcr_dose_rate` | radiation | numeric | mGy/d | 0 | — | spacecraft | — |
| `radiation_saa_dose_rate` | radiation | numeric | mGy/d | 0 | — | spacecraft | — |
| `radiation_total_dose_rate` | radiation | numeric | mGy/d | 0 | — | spacecraft | — |
| `radiation_accumulated_dose` | radiation | numeric | mGy | 0 | — | spacecraft | — |
| `cabin_co2_partial_pressure` | environmental | numeric | Pa | 0 | — | spacecraft, compartment | — |
| `sleep_duration` | behavioral | numeric | h | 0 | — | astronaut | — |
| `fatigue_self_report` | behavioral | categorical | — | — | — | astronaut | rested, tired, very_tired |
| `communication_delay` | mission_context | numeric | s | 0 | — | spacecraft, mission | — |
| `heart_rate` | physiological | numeric | bpm | 0 | — | astronaut | — |
| `ambient_pressure` | environmental | numeric | Pa | 0 | — | spacecraft, compartment | — |
| `absorbed_dose` | radiation | numeric | Gy | 0 | — | astronaut, spacecraft, compartment | — |
| `sleep_state` | behavioral | categorical | — | — | — | astronaut | awake, asleep |
| `gravity_magnitude` | altered_gravity | numeric | m/s2 | 0 | — | astronaut, spacecraft, compartment | — |
| `exercise_active` | mission_context | boolean | — | — | — | astronaut, mission | — |

Registry bounds are physical-domain checks, not clinical thresholds. The current
`evaluate_quality` function reports an out-of-range numeric value as
`invalid`/`physical_domain_violation` without discarding it. It does not mutate
the input contract. Decide whether this derived assessment is recomputed or
stored separately; do not overwrite the input `quality_status` or reason codes.
The database cannot express a cross-table bound with an ordinary row CHECK.

### `metric_allowed_scopes` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `metric_id` | `text` | PK part; FK `metric_definitions.metric_id` | No | Registry metric |
| `scope_kind` | `text` | PK part | No | `astronaut`, `spacecraft`, `compartment`, or `mission` |

Seed only scope combinations in `METRIC_REGISTRY`.

### `metric_categories` — required for categorical metrics

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `metric_id` | `text` | PK part; FK part to metric definition | No | Categorical metric |
| `metric_kind` | `text` | FK part; CHECK `categorical` | No | Registry's expected value type |
| `category` | `text` | PK part | No | Registry category, e.g. fatigue state |

Composite FK `(metric_id, metric_kind)` references
`metric_definitions(metric_id, metric_kind)` and the CHECK fixes the kind to
`categorical`; PK remains `(metric_id, category)` for categorical child refs.
This prevents non-categorical metrics from acquiring category rows. Do not seed
unsupported categories.

## Observation and ingestion

### `observations` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK | No | Proposed client-generated stable relational/sync ID |
| `observation_id` | `text` | Unique with source | No | Exact Observation v1 identifier |
| `schema_version` | `text` | — | No | Contract version; currently `1.0.0` |
| `event_at` | `timestamptz` | — | No | Contract `timestamp`; event time |
| `ingested_at` | `timestamptz` | — | Yes | Contract ingestion time; never substitutes for event time |
| `domain` | `text` | — | No | Observation v1 domain |
| `metric_id` | `text` | FK part to metric definition | No | Exact registry metric |
| `metric_kind` | `text` | FK part to metric definition | No | Proposed column mapping to registry `measurement_kind`; expected value type |
| `measurement_kind` | `text` | — | No | Proposed column mapping to Observation `measurement.kind`; actual numeric/boolean/categorical/unavailable variant |
| `scope_kind` | `text` | FK part to allowed scopes | No | Scope discriminator |
| `mission_id` | `text` | FK `missions.mission_id` | No | Present for all scope variants |
| `astronaut_id` | `text` | FK `astronaut_profiles.astronaut_id` | Yes | Only for astronaut scope |
| `spacecraft_id` | `text` | FK `spacecraft.spacecraft_id` | Yes | Spacecraft or compartment scope |
| `compartment_id` | `text` | Composite FK `compartments` | Yes | Only for compartment scope |
| `quality_status` | `text` | — | No | valid/suspect/invalid/missing/unavailable |
| `sensor_confidence` | `double precision` | — | Yes | Contract optional [0,1]; not confidence in model output |
| `source_type` | `text` | — | No | Contract provenance source type |
| `source_id` | `text` | — | No | Contract provenance source ID; not authenticated device identity |
| `method` | `text` | — | No | Contract provenance method |
| `origin` | `text` | — | No | measured/self_reported/derived/simulated |
| `transformation_version` | `text` | — | Yes | Required for derived origin |
| `simulation_scenario_id` | `text` | — | Yes | Simulation metadata only |
| `simulation_run_id` | `text` | — | Yes | Simulation metadata only |
| `simulation_generator_version` | `text` | — | Yes | Simulation metadata only |
| `simulation_seed` | `bigint` | — | Yes | Nonnegative simulation seed only |

Candidate unique `(source_type, source_id, observation_id)` and
`(record_id, metric_id, metric_kind, measurement_kind)` are proposed; also add
the referenced metric unique keys listed above. Confirm source identifier
semantics. Checks enforce scope-kind/null-column shape, time order,
`sensor_confidence` bounds, allowed source/origin pairs, and simulation metadata
all-present iff `origin='simulated'`. A deferred trigger enforces derived parent
rows. Parent IDs are represented by `observation_parent_references`, not a
string array. Do not enforce the candidate source identity uniqueness until
producer namespaces and duplicate/re-import behavior are approved.

The four Observation v1 scope models all require `mission_id`; it is contextual
mission association. The scope discriminator separately identifies astronaut,
spacecraft, compartment, or mission. For astronaut/spacecraft/compartment
scopes, the corresponding subject/location FK is required and all irrelevant
scope FKs are NULL; mission scope has none of those three FKs. A database FK
proves that each referenced row exists, not that its assignment was effective
at `event_at`.

The candidate unique key `(source_type, source_id, observation_id)` is not
verified as a global or cross-producer identity rule. NASA RR-1 derives stable
IDs from a file digest, row index, and column, but other sources and repeat
imports are not governed by that implementation. Do not enforce the candidate
until source identity and re-import semantics are approved.

Indexes: `(mission_id, event_at DESC)`, `(astronaut_id, event_at DESC)` partial
where non-null, `(spacecraft_id, event_at DESC)` partial, `(metric_id, event_at
DESC)`, and scope/time indexes shaped by reviewed query plans. Do not add a
generic GIN index before actual query need.

### Typed measurement subtables — required

Each child has one row per observation of its actual matching variant.
`metric_kind` is the registry's expected type; `measurement_kind` is the actual
contract variant. `record_id` is the child's PK; composite FK `(record_id,
metric_id, metric_kind, measurement_kind)` ties it to the parent. A deferred
constraint trigger requires exactly one matching subtype at commit. For
unavailable measurements, `metric_kind` can be numeric, boolean, or categorical.

Numeric values are finite by the Pydantic contract. The FK from child `unit` to
the registry's canonical unit enforces equality; it does not convert an input.
An approved source-specific conversion must occur in ingestion before contract
validation with an explicit mapping/version. Unknown conversions must be
rejected or quarantined. Physical min/max are evaluated by
`evaluate_quality`; out-of-range evidence is retained as invalid rather than
rejected. Persisting that derived assessment separately from input `DataQuality`
remains an architecture decision. PostgreSQL floating-point types can represent
special values, so DDL must explicitly reject `NaN` and infinities; a plain
`double precision` type does not by itself enforce finiteness.

#### `numeric_measurements`

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK; FK to observation composite | No | Parent observation |
| `metric_id` | `text` | FK to observation and metric definition | No | Numeric metric |
| `metric_kind` | `text` | FK; CHECK `numeric` | No | Registry expected type |
| `measurement_kind` | `text` | FK; CHECK `numeric` | No | Actual union variant |
| `value` | `double precision` | — | No | Finite source value; never impute missingness here |
| `unit` | `text` | FK with metric/kind to canonical unit | No | Exact contract unit; no implicit conversion |

#### `boolean_measurements`

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK; FK to observation composite | No | Parent observation |
| `metric_id` | `text` | FK to observation and metric definition | No | Boolean metric |
| `metric_kind` | `text` | FK; CHECK `boolean` | No | Registry expected type |
| `measurement_kind` | `text` | FK; CHECK `boolean` | No | Actual union variant |
| `value` | `boolean` | — | No | Exact boolean value; false is not absence |

#### `categorical_measurements`

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK; FK to observation composite | No | Parent observation |
| `metric_id` | `text` | FK to observation and metric definition | No | Categorical metric |
| `metric_kind` | `text` | FK; CHECK `categorical` | No | Registry expected type |
| `measurement_kind` | `text` | FK; CHECK `categorical` | No | Actual union variant |
| `value` | `text` | FK `(metric_id, category)` | No | Registry category |

#### `unavailable_measurements`

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK; FK to observation composite | No | Parent observation |
| `metric_id` | `text` | FK to observation and metric definition | No | Metric whose value is absent |
| `metric_kind` | `text` | FK to metric definition | No | Expected type of absent metric |
| `measurement_kind` | `text` | FK; CHECK `unavailable` | No | Actual union variant |
| `reason` | `text` | — | No | not_received/not_collected/sensor_offline/rejected |

The parent `quality_status` must agree with the unavailable reason: `not_received`
maps to `missing`; the other reasons map to `unavailable`.

### `observation_quality_reasons` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `record_id` | `uuid` | PK part; FK `observations.record_id` | No | Parent |
| `reason_code` | `text` | PK part | No | Exact contract reason; no unverified global vocabulary |

Reason cardinality and consistency with `quality_status` are deferred-validated.

### `observation_parent_references` — required

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `child_record_id` | `uuid` | PK part; FK observations | No | Derived record |
| `parent_record_id` | `uuid` | PK part; FK observations | No | Source evidence |

CHECK child differs from parent. Derived observation has at least one parent and
a transformation version; non-derived observations have neither. Acyclic graph
validation is not established by Observation v1 and remains a policy decision.

### `ingestion_batches` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `batch_id` | `uuid` | PK | No | Proposed import identity |
| `source_sha256` | `char(64)` | — | Yes | Source artifact digest when available |
| `manifest_sha256` | `char(64)` | — | Yes | Dataset manifest digest when available |
| `schema_version` | `text` | — | No | Import contract/version |
| `received_at` | `timestamptz` | — | No | Cloud receipt/ingestion time, distinct from event time |
| `status` | `text` | — | No | Proposed lifecycle; exact values need implementation review |

No source filename/path is persisted by default. Hash columns require lowercase
64-hex checks. Batch idempotency/re-import semantics are unresolved.

### `ingestion_source_rows` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `batch_id` | `uuid` | PK part; FK batch | No | Parent import |
| `row_number` | `bigint` | PK part | No | Source row number |
| `original_fields` | `jsonb` | — | No | Exact source tokens from NASA adapter; sensitive retention review required |
| `time_interpretation` | `text` | — | No | Adapter's explicit temporal assumption |
| `issue_codes` | `text[]` | — | No | Adapter issue codes; preserve empty as empty, not null |

`SourceRecord.source_file` is deliberately not represented as a persisted path
or filename. Whether a safe display name may be retained requires data
classification and retention approval. `original_fields` can contain raw
source tokens and must not be logged; approve its retention, redaction, and
access before persistence.

### `ingestion_observation_links` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `batch_id` | `uuid` | PK part; composite FK source row | No | Source batch |
| `row_number` | `bigint` | PK part; composite FK source row | No | Source row |
| `record_id` | `uuid` | PK part; FK observation | No | Emitted observation |

## AI and research

### `ai_models` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `model_id` | `text` | PK | No | Exact implemented model identifier when registered |

Do not pre-seed Model B; no implementation/contract exists. The M2 rule engine is
stored in `investigations`, not this model registry.

### `model_versions` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `version_id` | `uuid` | PK | No | Proposed relational identity |
| `model_id` | `text` | FK `ai_models.model_id` | No | Model |
| `model_version` | `text` | — | No | Exact contract version string |
| `metadata_schema_version` | `text` | — | Yes | Model A metadata schema version, if applicable |
| `feature_schema_version` | `text` | — | Yes | Feature contract version, if applicable |
| `artifact_sha256` | `char(64)` | — | Yes | Model A artifact integrity digest; Model C may have none |
| `metadata_payload` | `jsonb` | — | Yes | Optional exact versioned metadata snapshot |
| `created_at` | `timestamptz` | — | Yes | Model metadata time, if declared |

Unique `(model_id, model_version)`. Do not treat metadata as proof a model is
trained, provisioned, approved, or medically validated.

### `inference_runs` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `run_id` | `uuid` | PK | No | Proposed run identity |
| `model_version_id` | `uuid` | FK `model_versions.version_id` | No | Exact version executed |
| `request_schema_version` | `text` | — | Yes | Versioned input contract |
| `run_status` | `text` | — | No | Proposed transport lifecycle (`running`, `succeeded`, `failed`) |
| `started_at` | `timestamptz` | — | Yes | Execution metadata, not in all current contracts |
| `completed_at` | `timestamptz` | — | Yes | Execution metadata |
| `idempotency_key` | `uuid` | UNIQUE | Yes | Proposed stable request key for retries |
| `safe_error_code` | `text` | — | Yes | Error category only; no raw sensitive values |

`completed_at >= started_at` when both exist. These generic run columns must not
invent model-specific confidence, probability, or result status.

### `inference_input_references` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `run_id` | `uuid` | PK part; FK inference run | No | Run |
| `record_id` | `uuid` | PK part; FK observation | No | Actual input observation |
| `input_role` | `text` | PK part | No | Versioned integration role; don't infer unimplemented roles |

This table makes input lineage referentially valid. `observation_id` values in
contracts are resolved to a unique database `record_id` before insert.

### `inference_results` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `result_id` | `uuid` | PK | No | Proposed result row |
| `run_id` | `uuid` | FK inference run | No | Producing run |
| `result_type` | `text` | — | No | Existing contract family only; e.g. Model A context or Model C assessment |
| `schema_version` | `text` | — | No | Result contract version |
| `result_payload` | `jsonb` | — | No | Full validated, versioned result snapshot |
| `created_at` | `timestamptz` | — | No | Persistence time, distinct from `assessed_at` |

No shared contract result ID exists: Model C has `assessment_id`, while Model A
has no equivalent top-level result identifier. Keep model-specific IDs inside
their payloads; do not manufacture a cross-model ID. A proposed uniqueness or
idempotency key for each result family remains to be designed. Do not put M2
investigations here or merge output domains into one score schema.

### `inference_evidence` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `result_id` | `uuid` | PK part; FK result | No | Output |
| `record_id` | `uuid` | PK part; FK observation | No | Real referenced observation |
| `evidence_role` | `text` | PK part | No | Role defined by the stored result integration; no universal confidence semantics |

### `investigations` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `investigation_id` | `text` | PK | No | Exact M2 contract identifier |
| `schema_version` | `text` | — | No | Current Investigation schema `1.0.0` |
| `engine_version` | `text` | — | No | Current M2 producer `reference-rules-1.0.0` |
| `window_seconds` | `integer` | — | No | Positive M2 comparison window |
| `status` | `text` | — | No | ranked/ambiguous/insufficient_evidence/conflicting_evidence |
| `selected_hypothesis` | `text` | nullable composite FK part to `investigation_hypotheses.hypothesis_id` | Yes | M2 producer selects only for its ranked case; schema field itself is nullable |
| `safety_status` | `text` | — | No | Current literal `not_evaluated` |
| `result_payload` | `jsonb` | — | No | Full validated M2 Investigation snapshot |
| `persisted_at` | `timestamptz` | — | No | Storage time; result `timestamp` is separately preserved in payload |

No FK to inference runs: current M2 is a separate deterministic engine and has no
such relationship.

The producer sets `selected_hypothesis` to null when it abstains, but the
Pydantic output schema does not enforce that status/selection invariant. Validate
it at the persistence boundary. When non-null, the proposed deferred composite
FK `(investigation_id, selected_hypothesis)` ensures the selected ID belongs to
that same investigation; insertion of the investigation and its hypotheses
must occur in one transaction.

### `investigation_contexts` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `investigation_id` | `text` | PK part; FK investigation | No | Parent |
| `context_role` | `text` | PK part | No | CHECK `current` or `reference` |
| `sample_id` | `text` | — | No | SampleAnchor ID; no persisted sample table exists |
| `episode_id` | `text` | — | No | SampleAnchor context identifier |
| `mission_id` | `text` | FK missions | No | Context mission |
| `astronaut_id` | `text` | FK astronaut profiles | No | Context subject |
| `spacecraft_id` | `text` | FK spacecraft | No | Context spacecraft |
| `compartment_id` | `text` | Composite FK compartments | No | Context compartment |
| `context_at` | `timestamptz` | — | No | Exact SampleAnchor timestamp |

The current `SampleAnchor` contract requires all listed fields, so these are
non-null in this particular contract snapshot, not inferred generic scope rules.
The M2 request carries one `current` and one `reference` anchor. If normalized
context rows are retained, require exactly one of each for a persisted
investigation at commit (a deferred constraint or atomic transaction check).
Persist the investigation and both contexts together. Current and reference
contexts are separate: M2 permits an empirical comparator and does not establish
that it is “normal.”

### `investigation_hypotheses` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `investigation_id` | `text` | PK part; FK investigation | No | Parent |
| `hypothesis_id` | `text` | PK part | No | Exact hypothesis identifier |
| `rank` | `integer` | — | No | Positive rank; ties are allowed |
| `compatibility` | `text` | — | No | Current qualitative compatibility enum |
| `hypothesis_payload` | `jsonb` | — | No | Exact hypothesis result and nested findings |

Rank is not unique because ties are valid. Do not interpret rank as probability.

### `investigation_observation_refs` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `reference_id` | `uuid` | PK | No | Proposed junction identity |
| `investigation_id` | `text` | FK investigation | No | Parent investigation |
| `hypothesis_id` | `text` | Composite FK to hypothesis | Yes | Null for whole-window input lineage |
| `record_id` | `uuid` | FK observation | No | Existing observation row |
| `window_kind` | `text` | — | No | `current` or `reference` |
| `reference_role` | `text` | — | No | `window_input`, supporting, contradictory, quality, or other contract-mapped role |
| `metric_id` | `text` | — | Yes | Finding metric where applicable |
| `relation` | `text` | — | Yes | Exact EvidenceRelation where applicable |

CHECK requires a null `hypothesis_id` only for `window_input`; hypothesis-specific
rows require that hypothesis to belong to the same investigation. Missing
findings with empty ID arrays have no fake observation FK row; full absence and
reason remain in the JSONB contract snapshot.

## Operations and synchronization

### `audit_events` — optional

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `event_id` | `uuid` | PK | No | Proposed append-only event ID |
| `actor_user_id` | `uuid` | FK profiles | Yes | Null for system event |
| `event_code` | `text` | — | No | Safe action category; vocabulary to be approved |
| `occurred_at` | `timestamptz` | — | No | Server event time |
| `correlation_id` | `text` | — | Yes | Safe request correlation identifier |
| `details` | `jsonb` | — | No | Allowlisted non-sensitive metadata only; never tokens/health payloads |

Do not use an unconstrained audit pointer as an authorization relationship.
Read-audit granularity and retention remain unresolved.

### `sync_operations` — optional cloud idempotency receipt

| Column | Type | PK/FK | Null? | Constraint / meaning |
|---|---|---|---|---|
| `operation_id` | `uuid` | PK | No | Client-generated idempotency key; reused unchanged for retries |
| `submitted_by_user_id` | `uuid` | FK profiles | Yes | Set by server from verified Auth context; never trusted from payload |
| `origin_install_id` | `uuid` | — | No | Proposed opaque local installation identity, not user identity |
| `operation_kind` | `text` | — | No | Approved sync operation vocabulary |
| `payload_sha256` | `char(64)` | — | No | Detects same idempotency key reused for different content |
| `status` | `text` | — | No | received/applied/conflict/rejected; exact state machine to be approved |
| `received_at` | `timestamptz` | — | No | First cloud receipt |
| `completed_at` | `timestamptz` | — | Yes | Completion time |
| `outcome_code` | `text` | — | Yes | Safe retry/conflict outcome code |

This optional receipt proposal assumes the same `operation_id` and digest return
the original result and the same ID with a different digest is rejected; domain
writes and receipt recording would need one transaction. The ledger contains no
arbitrary `entity_type/entity_id` FK and no raw payload. This does not specify a
local outbox, durable pending-operation format, retry/backoff, delivery
acknowledgment, reconciliation, or conflict resolution. All of those, plus
offline identity and revocation behavior, require a separate synchronization
architecture decision; merge/conflict policy must not default to last-write-wins.

## Index, consistency, and open-schema notes

- Index all FKs used in joins and scopes; PostgreSQL does not automatically index
  FK columns. Prioritize event-time queries by mission, subject, metric, and
  spacecraft; confirm composite ordering using workload measurements.
- Use partial unique indexes for active role grants and active assignments.
- Use deferred constraint triggers for measurement subtype cardinality,
  quality-reason consistency, simulation/derived provenance, and the pair of
  investigation contexts. Trigger behavior requires integration tests.
- Preserve `timestamptz`; do not store mission-relative time as UTC or infer one
  from the other. The current Observation contract has no mission-relative time.
- JSONB snapshots remain versioned and validated at the application boundary.
  Do not assume PostgreSQL JSONB validation alone enforces nested Pydantic
  contracts.
- Model-specific numerical result fields remain in their exact payloads:
  Model A anomaly scores are not probabilities; Model C sleep findings and
  fatigue counts are not a composite score; M2 compatibility is qualitative.
  No Model B schema is supplied.
- Retention, deletion/anonymization, encryption-at-rest, local-store technology,
  sync conflict semantics, profile-to-subject cardinality, and source ID
  uniqueness require architecture/security approval before SQL implementation.
