# CAREYONDA Database Relationship Specification

This is a proposed relationship contract, not executable DDL. PostgreSQL is the
primary data store; Supabase is optional. Identifiers and fields marked here are
design additions unless they are explicitly identified as contract fields in
[ERD.md](./ERD.md). Historical entities are ended, not overwritten.

`RESTRICT` is the default for evidence-bearing parent records. `CASCADE` is
limited to dependent subtype/junction rows whose meaning cannot outlive their
parent. Primary keys are immutable (`ON UPDATE RESTRICT`). Hard-delete,
retention, and anonymization policy is unresolved.

## Parent/child relationship matrix

| Parent | Child | Foreign key | Cardinality | Optional? | Delete/update behavior |
|---|---|---|---|---|---|
| `auth.users` (Supabase-managed) | `profiles` | `profiles.id → auth.users.id` | 1:0..1 | Yes; only app users have a profile | Delete restricted; suspend app profile |
| `profiles` | `user_roles` (user) | `user_roles.user_id → profiles.id` | 1:M | No | Restrict; revoke grant, do not delete |
| `profiles` | `user_roles` (grantor) | `user_roles.assigned_by_user_id → profiles.id` | 1:M | No | Restrict; retain audit attribution |
| `profiles` | `astronaut_profiles` | `astronaut_profiles.user_id → profiles.id` | 1:0..1 | Yes | Set null only on approved unlink |
| `profiles` | `doctor_profiles` | `doctor_profiles.user_id → profiles.id` | 1:0..1 | No for doctor account | Restrict; suspend/unassign |
| `doctor_profiles` | `doctor_astronaut_assignments` | `doctor_id → doctor_profiles.doctor_id` | 1:M | No | Restrict; end assignment |
| `astronaut_profiles` | `doctor_astronaut_assignments` | `astronaut_id → astronaut_profiles.astronaut_id` | 1:M | No | Restrict; end assignment |
| `profiles` | `doctor_astronaut_assignments` (grantor) | `assigned_by_user_id → profiles.id` | 1:M | No | Restrict |
| `profiles` | `doctor_astronaut_assignments` (ender) | `ended_by_user_id → profiles.id` | 1:M | Yes until assignment ends | Restrict |
| `missions` | `mission_crew_assignments` | `mission_id → missions.mission_id` | 1:M | No | Restrict; retain mission history |
| `astronaut_profiles` | `mission_crew_assignments` | `astronaut_id → astronaut_profiles.astronaut_id` | 1:M | No | Restrict; end membership |
| `profiles` | `mission_crew_assignments` (grantor) | `assigned_by_user_id → profiles.id` | 1:M | No | Restrict |
| `missions` | `mission_spacecraft_assignments` | `mission_id → missions.mission_id` | 1:M | No | Restrict |
| `spacecraft` | `mission_spacecraft_assignments` | `spacecraft_id → spacecraft.spacecraft_id` | 1:M | No | Restrict |
| `profiles` | `mission_spacecraft_assignments` (grantor) | `assigned_by_user_id → profiles.id` | 1:M | No | Restrict |
| `spacecraft` | `compartments` | `spacecraft_id → spacecraft.spacecraft_id` | 1:M | No | Restrict; compartment key is spacecraft-scoped |
| `metric_definitions` | `metric_allowed_scopes` | `metric_id → metric_definitions.metric_id` | 1:M | No | Restrict; version registry changes |
| `metric_definitions` | `metric_categories` | `(metric_id, metric_kind) → metric_definitions(metric_id, metric_kind)` | 1:M | No | Restrict; child fixes `metric_kind` to `categorical` |
| `missions` | `observations` | `mission_id → missions.mission_id` | 1:M | No | Restrict; mission context is present independently of scope identity |
| `astronaut_profiles` | `observations` | `astronaut_id → astronaut_profiles.astronaut_id` | 1:M | Scope-dependent | Restrict |
| `spacecraft` | `observations` | `spacecraft_id → spacecraft.spacecraft_id` | 1:M | Scope-dependent | Restrict |
| `compartments` | `observations` | `(spacecraft_id, compartment_id) → compartments` composite PK | 1:M | Compartment scope only | Restrict |
| `metric_definitions` | `observations` | `(metric_id, domain, metric_kind) → metric_definitions` unique key | 1:M | No | Restrict; `metric_kind` maps the registry's expected type |
| `metric_allowed_scopes` | `observations` | `(metric_id, scope_kind) → metric_allowed_scopes` PK | 1:M | No | Restrict |
| `observations` | `numeric_measurements` | `(record_id, metric_id, metric_kind, measurement_kind) → observations` unique key | 1:0..1 | When actual variant is not numeric | Cascade subtype with parent; deferred exact-one check |
| `observations` | `boolean_measurements` | `(record_id, metric_id, metric_kind, measurement_kind) → observations` unique key | 1:0..1 | When actual variant is not boolean | Cascade subtype with parent; deferred exact-one check |
| `observations` | `categorical_measurements` | `(record_id, metric_id, metric_kind, measurement_kind) → observations` unique key | 1:0..1 | When actual variant is not categorical | Cascade subtype with parent; deferred exact-one check |
| `observations` | `unavailable_measurements` | `(record_id, metric_id, metric_kind, measurement_kind) → observations` unique key | 1:0..1 | When actual value is available | Cascade subtype with parent; deferred exact-one check |
| `metric_definitions` | `numeric_measurements` | child `(metric_id, metric_kind, unit) → (metric_id, metric_kind, canonical_unit)` | 1:M | No | Restrict; enforces canonical unit |
| `metric_definitions` | `boolean_measurements` | `(metric_id, metric_kind) → metric_definitions` unique key | 1:M | No | Restrict |
| `metric_definitions` | `categorical_measurements` | `(metric_id, metric_kind) → metric_definitions` unique key | 1:M | No | Restrict |
| `metric_categories` | `categorical_measurements` | `(metric_id, category) → metric_categories` PK | 1:M | No | Restrict |
| `metric_definitions` | `unavailable_measurements` | `(metric_id, metric_kind) → metric_definitions` unique key | 1:M | No | Restrict; unavailable can represent any registry kind |
| `observations` | `observation_quality_reasons` | `record_id → observations.record_id` | 1:M | Zero only for valid | Cascade dependent reasons |
| `observations` | `observation_parent_references` (derived child) | `child_record_id → observations.record_id` | 1:M | Non-derived records have none | Restrict |
| `observations` | `observation_parent_references` (source parent) | `parent_record_id → observations.record_id` | 1:M | Parents can have no children | Restrict |
| `ingestion_batches` | `ingestion_source_rows` | `batch_id → ingestion_batches.batch_id` | 1:M | A batch may have none | Restrict after acceptance |
| `ingestion_source_rows` | `ingestion_observation_links` | `(batch_id, row_number) → ingestion_source_rows` PK | 1:M | Source row may emit zero/many | Restrict |
| `observations` | `ingestion_observation_links` | `record_id → observations.record_id` | 1:M | Not all observations are batch-ingested | Restrict |
| `ai_models` | `model_versions` | `model_id → ai_models.model_id` | 1:M | Model may have no versions | Restrict; versions immutable |
| `model_versions` | `inference_runs` | `model_version_id → model_versions.version_id` | 1:M | Version may not have runs | Restrict |
| `inference_runs` | `inference_input_references` | `run_id → inference_runs.run_id` | 1:M | Empty/failed run may have none | Cascade only with approved run purge |
| `observations` | `inference_input_references` | `record_id → observations.record_id` | 1:M | Observation may not be model input | Restrict |
| `inference_runs` | `inference_results` | `run_id → inference_runs.run_id` | 1:M | Failed run may have none | Restrict |
| `inference_results` | `inference_evidence` | `result_id → inference_results.result_id` | 1:M | Result may have none | Cascade dependent reference rows |
| `observations` | `inference_evidence` | `record_id → observations.record_id` | 1:M | Observation may not be evidence | Restrict |
| `investigations` | `investigation_contexts` | `investigation_id → investigations.investigation_id` | 1:2 | Exactly two required | Restrict; context snapshots immutable |
| `missions` | `investigation_contexts` | `mission_id → missions.mission_id` | 1:M | No | Restrict |
| `astronaut_profiles` | `investigation_contexts` | `astronaut_id → astronaut_profiles.astronaut_id` | 1:M | No | Restrict |
| `spacecraft` | `investigation_contexts` | `spacecraft_id → spacecraft.spacecraft_id` | 1:M | No | Restrict |
| `compartments` | `investigation_contexts` | `(spacecraft_id, compartment_id) → compartments` composite PK | 1:M | No | Restrict |
| `investigations` | `investigation_hypotheses` | `investigation_id → investigations.investigation_id` | 1:M | Contract permits empty tuple; producer rule to confirm | Restrict |
| `investigation_hypotheses` | `investigations` (selected hypothesis) | `(investigation_id, selected_hypothesis) → investigation_hypotheses(investigation_id, hypothesis_id)` PK | 0..1:0..1 | Yes when result has no selection | `RESTRICT`; deferred FK; selected ID must belong to same investigation |
| `investigations` | `investigation_observation_refs` | `investigation_id → investigations.investigation_id` | 1:M | Yes | Restrict |
| `investigation_hypotheses` | `investigation_observation_refs` | `(investigation_id, hypothesis_id) → investigation_hypotheses` PK | 1:M | Yes for window-only refs | Nullable FK; null means whole-window lineage |
| `observations` | `investigation_observation_refs` | `record_id → observations.record_id` | 1:M | Observation may not be referenced | Restrict |
| `profiles` | `audit_events` | `actor_user_id → profiles.id` | 1:M | Yes for system events | Restrict |
| `profiles` | `sync_operations` | `submitted_by_user_id → profiles.id` | 1:M | Yes until authenticated | Restrict |

The `auth.users` relation is external to CAREYONDA's public tables. Counting the
58 parent/child rows above yields **58 FK constraints**: each matrix row
describes one FK, including the single external `auth.users` → `profiles` FK.
Composite-column FKs count once, not once per column. This is a document count,
not a validated DDL count; re-count against the approved migration before SQL is
reviewed.

## Many-to-many links

| Left side | Junction | Right side | Notes |
|---|---|---|---|
| Profiles | `user_roles` | Roles | Role values: Admin, Doctor, Astronaut; grants are historical |
| Doctors | `doctor_astronaut_assignments` | Astronauts | Effective-dated; only active duplicate pair prohibited |
| Missions | `mission_crew_assignments` | Astronauts | Historical membership intervals |
| Missions | `mission_spacecraft_assignments` | Spacecraft | Historical mission/location intervals |
| Metrics | `metric_allowed_scopes` | Scope kinds | Scope kind has a finite vocabulary |
| Metrics | `metric_categories` | Categorical values | Only categories defined by the metric registry |
| Observations | `observation_parent_references` | Observations | Directed provenance edge, self-FK |
| Inference runs | `inference_input_references` | Observations | Input lineage |
| Inference results | `inference_evidence` | Observations | Output evidence lineage |
| Investigations | `investigation_observation_refs` | Observations | Whole-window and hypothesis-specific evidence |
| Ingestion rows | `ingestion_observation_links` | Observations | One source row may emit multiple records |

## Composite and temporal constraints

- `compartments` has primary key `(spacecraft_id, compartment_id)`.
- `metric_categories(metric_id, metric_kind)` references the corresponding
  unique registry key, and a CHECK fixes `metric_kind` to `categorical`.
- Every Observation v1 scope variant includes a required `mission_id`; it is
  contextual mission association, while `scope_kind` plus its specific
  identifier defines astronaut, spacecraft, compartment, or mission scope.
  Irrelevant scope identifiers must be NULL.
- Metric/scope and metric/category junctions use composite primary keys.
- `metric_kind` is the registry's expected value type. `measurement_kind` is the
  contract's actual tagged-union variant, including `unavailable`; keep them
  distinct so an unavailable numeric metric remains relationally valid.
- Measurement child tables carry the `metric_id`, `metric_kind`, and fixed
  `measurement_kind` needed for composite FKs; they do not duplicate untrusted
  arbitrary references.
- `observations` has composite unique keys for its metric and typed union.
- Assignment tables retain `starts_at`, nullable `ended_at`, and actor references.
  Partial unique indexes should reject duplicate active pairs. `ended_at` must be
  later than `starts_at`. Whether interval overlap across reassignments is
  prohibited remains to be decided.
- An FK can guarantee that the subject, mission, spacecraft, and compartment
  exist. It cannot alone guarantee their assignment was effective at an event
  timestamp. Enforce that temporal rule in a backend transaction or reviewed
  database function/trigger.
- Cross-table role/profile invariants are not ordinary FK constraints: a Doctor
  grant must correspond to a Doctor profile, and an Astronaut grant must
  correspond to its linked astronaut subject profile. Define them explicitly;
  enforce atomically in trusted backend transactions and consider a deferred
  trigger if other writers exist. Admin has no corresponding subtype profile.
  These cross-table checks are separate from the 58 FK count.
- `investigation_contexts` stores both current and reference `SampleAnchor`
  snapshots. `sample_id` and `episode_id` remain contract identifiers, not FKs:
  no persisted sample/episode entity currently exists.
- `SampleAnchor` currently requires mission, astronaut, spacecraft, compartment,
  sample/episode IDs, and a timestamp; the `InvestigationRequest` requires both
  current and reference anchors. If context rows are persisted, their exact-one
  pair rule applies to a completed persisted result and must be checked at
  transaction commit. It is not a generic scope rule.
- Missing evidence can have empty contract observation-ID arrays. Store that
  missingness in the versioned payload; do not fabricate an observation row or
  zero-value measurement to satisfy a FK.
- The contract requires exact canonical numeric units and does not convert.
  Approved source-specific unit conversion belongs in ingestion before
  validation; unknown mappings are rejected/quarantined. `evaluate_quality`
  reports physical-bound violations as invalid without discarding the
  observation. The current table model does not distinguish source quality from
  this derived assessment; resolve recomputation versus separate persistence.
- The three assignment tables record assigning actors, but only
  `doctor_astronaut_assignments` currently has an ending-actor FK. Decide whether
  mission assignment closure actors need FKs or a reviewed audit event.
- `sync_operations` represents only a proposed server-side idempotency receipt.
  It does not define the offline outbox, retries, reconnection, reconciliation,
  or conflict resolution; those require a separate synchronization specification.

## Deletion, update, and lifecycle policy

Use `RESTRICT` for missions, subjects, locations, observations, model versions,
investigation results, and actors referenced by history. `CASCADE` is appropriate
only for dependent typed measurement rows and quality/junction rows when a
separate approved retention operation deletes the owning observation. Auth
account suspension is an update to `profiles.status`, not row deletion.
Assignment closure and role revocation set `ended_at`/`revoked_at`; they do not
delete history. Parent keys are immutable. No broad cascade from `profiles` to
health evidence is permitted.
