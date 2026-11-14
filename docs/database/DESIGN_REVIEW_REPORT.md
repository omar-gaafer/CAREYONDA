# CAREYONDA Database Design Review Report

**Review outcome: Not ready for architecture approval.** The three design
documents are materially more consistent and are grounded in the inspected
contracts, but key decisions about local identity/storage, synchronization,
authorization, privacy/retention, and derived quality remain open. This review
is documentation-only; no schema or database is implemented.

## 1. Executive summary

Reviewed and revised the proposed ERD, relationship matrix, and data dictionary
against the current Observation v1, M2, Model A, Model C, NASA RR-1 ingestion,
local API, and local storage code. Corrections distinguish verified contract
facts from proposed relational design and unresolved policy. The final
relationship matrix contains **58 FK constraints** (including one external
Supabase Auth FK), with each row counted as one constraint and composite FKs
counted once.

The observation design still correctly preserves all four scope discriminators
and their required mission context, and distinguishes registry expected
`metric_kind` from actual `measurement_kind`. The strongest blockers are that
the application has no durable observation DB or offline sync system; no
identity/role/assignment policy has been approved; metric physical quality is
derived separately from input `DataQuality`; and source identity, raw-ingestion
retention, and conflict behavior lack decisions.

## 2. Files reviewed

- `AGENTS.md`
- `docs/database/ERD.md`
- `docs/database/RELATIONSHIPS.md`
- `docs/database/DATA_DICTIONARY.md`
- Observation, investigation, SampleAnchor, evidence, Model A and Model C
  schema/implementation files listed below
- Local route composition, request/API contracts, quality evaluation, local
  evidence source, and NASA RR-1 ingestion implementation
- Relevant architecture documentation and storage/API code discovered during
  the audit

## 3. Source contracts inspected

- `backend/app/schemas/observation.py`: Observation v1 models, four scope
  variants, tagged measurement union, quality, provenance, metric registry, and
  contract validation.
- `backend/app/quality/validator.py`: physical-bound quality evaluation. An
  out-of-bound numeric observation is reported as invalid with
  `physical_domain_violation`; the source object is not mutated.
- `backend/app/features/temporal_features.py`: `SampleAnchor` requires all
  sample, episode, mission, astronaut, spacecraft, compartment, and timestamp
  fields.
- `backend/app/schemas/investigation.py`, `backend/app/schemas/evidence.py`, and
  `backend/app/ai/hazard_reasoning.py`: M2 result shape, nullable selection,
  possibly empty evidence arrays, hypothesis results, deterministic engine
  version/ID generation, and evidence references.
- `backend/app/schemas/environmental_anomaly_context.py` and
  `backend/app/storage/nasa_environment_model_store.py`: Model A identity,
  version/artifact/dataset metadata and local artifact persistence. No shared
  top-level result ID equivalent to Model C's assessment ID was verified.
- `backend/app/schemas/isolation_confinement.py`: Model C request/result
  contract, model/version/method and assessment IDs, intervals, data origin,
  evidence, and abstention states.
- `backend/app/ingestion/nasa_rr1.py`: source file digest/name, row number, raw
  fields, source observation IDs, time interpretation, issue codes, and
  deterministic RR-1 observation IDs.
- `backend/app/api/routes.py`, `backend/app/api/contracts.py`,
  `backend/app/api/security.py`, and `backend/app/main.py`: local synthetic
  API, pagination/filter query shape, no-auth statement, request guards, and
  non-persistent M2 behavior.
- `backend/app/storage/local_evidence.py`: configured JSON synthetic fixture
  loading and validation; this is not durable user observation storage.

## 4. Issues identified and fixed

1. Clarified that “required” means required within a proposed persistence model,
   not an implemented or approved feature.
2. Explicitly verified `mission_id` on each Observation scope and described it
   as context distinct from astronaut/spacecraft/compartment/mission scope
   identity. Specified null requirements for irrelevant scope identifiers and
   the composite compartment-to-spacecraft relationship.
3. Added the exact 17-metric registry snapshot: domains, expected kinds,
   canonical units, physical bounds, permitted scopes, and categorical values.
   No metric or threshold was invented.
4. Documented that source numeric unit conversion is not performed by the
   Observation contract; exact canonical units are required. Conversion, if
   approved, belongs in an explicit source adapter. Unknown conversions must
   not be guessed. The PostgreSQL representation must also explicitly reject
   `NaN` and infinities; `double precision` alone does not ensure finite values.
5. Separated source `DataQuality` from physical-bound evaluation and recorded
   that deciding recomputation versus separate persisted evaluation is open.
6. Specified that `metric_categories` must reference a categorical registry
   definition, not merely a metric ID.
7. Added role/profile consistency caveats: ordinary FKs cannot alone guarantee
   role-specific profiles and grants correspond. Trusted atomic enforcement
   and possible deferred constraint checks require approval.
8. Documented missing end-actor fields on mission assignment records and left
   interval-overlap policy unresolved.
9. Verified that the current M2 anchors contain all scope IDs and that persisted
   normalized contexts require one `current` and one `reference` row. Added a
   same-investigation FK for a non-null selected hypothesis; producer status/
   selection consistency still requires boundary validation.
10. Clarified that `sync_operations` only proposes a cloud receipt; it is not an
    offline outbox, retry/reconciliation protocol, or conflict-resolution
    design.
11. Removed a proposed generic `contract_result_id` field because Model A and
    Model C do not share that contract field. Model-specific identifiers remain
    in their versioned payloads until a persistence key is approved.
12. Reclassified the `(source_type, source_id, observation_id)` uniqueness
    assumption as unresolved. RR-1 constructs IDs deterministically, but that
    does not establish a cross-source or repeated-import uniqueness rule.
13. Recalculated FK count after adding the selected-hypothesis membership FK:
    **58 matrix relationships, 58 constraints**.

## 5. Decisions verified against code

| Topic | Verified finding |
|---|---|
| Observation scope | All four scope variants require `mission_id`; astronaut requires `astronaut_id`; spacecraft requires `spacecraft_id`; compartment requires spacecraft and compartment IDs; mission has only mission ID. |
| Registry type vs. observation variant | Registry `measurement_kind` is numeric/boolean/categorical; the observation union also allows `unavailable`. The database proposal names the former `metric_kind`. |
| Units and values | Numeric values are finite and must exactly match the registry canonical unit. No implicit unit conversion is implemented. |
| Physical bounds | Current quality evaluation checks registry min/max and reports invalidity without mutating/discarding the input observation. These bounds are not clinical thresholds. |
| Quality fields | Non-valid input quality requires reason codes; valid input quality forbids them; missing/unavailable forbids sensor confidence. The unavailable measurement reason is separately constrained and aligned with status. |
| Provenance | Derived observations require at least one unique, non-self parent and a transformation version. Simulated origin requires simulation metadata. Source type/origin pairs are constrained. |
| M2 | Investigation output carries sample IDs and timestamps, observation-ID tuples, hypotheses, qualitative status, and `safety_status="not_evaluated"`. Empty evidence tuples are structurally possible. |
| Model A / C | Model A exposes a model identity/version and artifact/dataset hashes in its research contract. Model C exposes model/version and `assessment_id`; neither validates a universal result-row ID. |
| Persistence/auth | Current API is local synthetic data, unauthenticated, and does not persist investigations. Supabase/Auth/RLS and durable observation persistence are not implemented. |
| NASA import | An RR-1 source row may emit multiple observation IDs; the adapter preserves raw row tokens and source metadata in an in-memory result object. This does not establish general ingestion cardinality or retention policy. |

## 6. Proposed design additions

- PostgreSQL relational tables, UUID `record_id`, indexes, JSONB snapshots,
  typed measurement subtables, FKs, and deferred integrity checks.
- Supabase profiles/roles and identity mappings, doctor/astronaut assignments,
  audit records, server-side sync receipts, and optional AI/M2 persistence.
- Role/profile consistency enforcement, temporal checks, result-lineage
  normalization, and append/end history semantics.
- Unit conversion/versioning in source adapters if an approved input source
  needs conversion.

None of these additions should be read as existing application behavior.

## 7. Unresolved architecture decisions

| Decision | Why it matters | Available evidence | Recommended options | Required approver |
|---|---|---|---|---|
| Local durable storage and local identity | Offline operation cannot depend on Supabase; affects ownership and sync keys. | Current API reads configured synthetic JSON and memory; no durable observation DB or auth. | Select a local store and offline identity model in a separate architecture decision; keep cloud adapter optional. | Architecture / product security |
| Sync protocol and conflicts | A receipt alone cannot safely reconcile concurrent offline edits or retries. | No local outbox/retry protocol exists. | Specify operation format, stable IDs, ordering, retry/backoff, duplicate delivery, conflict detection/resolution, and reconnection behavior before implementation. | Architecture |
| Auth bootstrap, roles, suspension, and profile invariants | Prevent privilege escalation and mismatched Doctor/Astronaut access, including through already-issued sessions. | Current API explicitly has no authentication; target roles are not implemented. | Approve provisioning, role grants/revocation, multi-role rules, role-profile invariant, trusted transaction/trigger boundary, and suspension token/session revocation semantics. | Product security / identity owner |
| Doctor access after assignment ends | Determines historical medical record visibility and RLS/API predicates. | Proposed effective-dated assignments; no current authorization contract. | Decide current-only vs. historical access, mission membership effects, and access audit. | Clinical governance / product security |
| Assignment overlap and closure attribution | Affects temporal authorization and trustworthy history. | Assignment rows are proposed; no overlap or closure-actor policy exists. | Approve overlap semantics and whether closure actors are stored on each assignment or in audit events. | Mission operations / architecture |
| Quality assessment persistence | Avoid overwriting source quality and retain evaluator provenance/version. | Evaluator derives `physical_domain_violation` without mutating input. | Recompute deterministically on read, or persist a separate versioned quality assessment. | Data governance / architecture |
| Source-unit conversion | Wrong conversions corrupt evidence and model inputs. | Contract accepts canonical units only; no generic converter verified. | Reject noncanonical source values unless a source-specific, versioned conversion is reviewed and tested. | Data engineering / domain owner |
| Source ID uniqueness and re-imports | A unique constraint could reject legitimate records or allow duplicates. | RR-1 ID includes file digest/row/column; other sources are unspecified. | Define producer namespace and idempotency key before adopting any uniqueness constraint. | Ingestion owner |
| Raw source retention | NASA row tokens and file metadata may carry licensing or sensitive content. | RR-1 adapter retains raw fields in memory; no persistence policy found. | Exclude raw fields, retain an allowlisted/redacted subset, or approve encrypted restricted retention. | Data governance / legal / security |
| M2 persistence and context requirements | Normalized records must reproduce the validated result without fabricating data. | Current M2 uses two complete SampleAnchors; endpoints do not persist results. | Persist a versioned snapshot and normalized references only if retrieval is required; write result and exactly two contexts atomically. | Product / architecture |
| Model output persistence keys | Avoid invented common model schema and unsafe deduplication. | Model A has no common result ID; Model C has `assessment_id`. | Keep model-specific IDs inside snapshots and define separate idempotency only when persistence workflows are approved. | AI owners / architecture |
| Retention, deletion, anonymization, backups | FK delete behavior cannot substitute for legal/clinical retention policy. | No approved policy found. | Establish retention and subject-rights policy before hard-delete or cascade decisions. | Governance / legal / security |
| Administrative vs. medical access and RLS | Prevent admin capability from implying access to sensitive health evidence. | No existing auth/RLS implementation. | Define API authorization and RLS as separate defense-in-depth controls; test with least-privileged identities. | Product security / clinical governance |

## 8. Cross-document consistency results

- All three schema documents retain the same 35 proposed CAREYONDA entities;
  external `auth.users` is not counted as a CAREYONDA table.
- The data dictionary declares composite keys for metric registry references,
  measurement parents, metric categories, compartment references, source-row
  references, and investigation hypotheses.
- The relationship matrix identifies 58 FK constraints; composite FKs count
  once. One is explicitly external (`auth.users` to `profiles`).
- FK target columns were cross-checked against the data dictionary's declared
  PK/unique shapes, including typed-observation parents, canonical units,
  categorical values, compartments, source rows, and same-investigation
  hypothesis selection.
- No claim is made that a database implementation was tested. DDL does not exist,
  so a migration-level catalog verification of FK targets, trigger behavior,
  cardinalities, and delete actions is not possible.
- Mermaid blocks were inspected for entity/relationship consistency. No Mermaid
  parser is installed; no package was installed.

## 9. Final FK count and method

**58 proposed FK constraints**, counting each row of
`RELATIONSHIPS.md`'s parent/child matrix once, including one explicitly marked
external Supabase `auth.users` → `profiles` FK. Composite FKs count as one
constraint regardless of their number of columns. This is a specification
count, not an executable DDL count.

## 10. Implementation and approval status

No SQL, migration, database function, Supabase configuration, application code,
AI implementation, database operation, package installation, or Git operation
was performed. The three design documents and this report are proposals only.

**Recommendation: Not ready for architecture approval.** Resolve the blocking
decisions in Section 7, especially offline storage/sync, identity/authorization,
source and retention rules, and quality persistence. Then conduct architecture
and security review before drafting DDL. Documentation consistency alone does
not establish production readiness or medical/operational suitability.
