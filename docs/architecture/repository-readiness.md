# Repository readiness and M1.1 recommendation

Review date: 2026-11-13. Scope: existing files, directory layout, Git state, and local Python availability. No packages installed, Git staging changed, or AI modules implemented.

## Readiness assessment

The repository is ready for contract design, but is not runnable or ready for inference, integration, or safety validation. At inspection, all 48 tracked/indexed files were zero-byte placeholders. New documents from this review are not included in that baseline count.

Git is initialized on `main` with no commits. The 48 existing files are staged additions; there is no initial commit to review. The review preserves that index state and makes no commit.

| Area | Observed state | Consequence / recommendation |
| --- | --- | --- |
| `README.md` | Empty | Document purpose, research status, layout, supported interpreter, offline setup, and commands once selected and verified. |
| `.gitignore` | Empty | Before adding local data or environments, add reviewed exclusions for secrets, virtual environments, caches, coverage, local databases and generated artifacts; preserve `.env.example` and synthetic fixtures. Ignore rules do not protect files already staged. |
| `.env.example`, `app/core/config.py` | Empty | No configuration contract. Define only settings actually required; use safe local defaults and validate them. |
| `backend/requirements.txt` | Empty | No dependencies or version constraints declared; no lockfile, packaging metadata, or development tool configuration found. Required packages cannot be inferred as installed or missing from imports because all source files are empty. |
| Backend | Empty `main.py` and placeholders for API, schemas, ingestion, quality, features, storage, AI, safety | No runnable server, database, validation, reasoning, or safety enforcement. Package directories are sensible; preserve their boundaries. |
| Knowledge | Empty `hazard_graph.yaml` and `references.yaml` | No supported hazard relationships, references, or approved procedures. Do not populate invented clinical rules. |
| Tests | Empty package and unit/integration markers | No executable behavior tests or test configuration. |
| Simulator / frontend / scripts / configs | Placeholder files or directories | No data generator, interface, run scripts, or configuration examples. |
| Datasets | Directory structure only | Empty directories are not represented in Git unless files are present. Define private-data handling and synthetic fixture locations before adding data. |
| Toolchain | Local `python3` reports 3.14.8; `rg` unavailable | Interpreter support is not declared or validated. Choose a supported target and verify dependency compatibility before approving installation. `find` was used for inventory. |

No runtime framework, schema library, database engine, or test runner has been selected by the repository. Proposals such as Pydantic for boundary validation and pytest for tests require a dependency decision and installation approval. A web framework, numerical stack, graph engine, and model runtime are unnecessary for M1.1.

## Architecture recommendation

Keep the existing layout. Establish a versioned evidence contract in `backend/app/schemas` before implementing ingestion or inference. A common contract prevents each future module from inventing incompatible time, provenance, quality, and uncertainty conventions. It should remain independent of HTTP, persistence, and model implementations.

Use a small common evidence envelope with explicitly typed payload variants rather than an unvalidated arbitrary dictionary. Keep observations distinct from derived evidence: source measurements belong to the observation contract, while derived records reference their inputs. `investigation.py` can later aggregate evidence identifiers without embedding inference policy in the schema.

These are proposed contract boundaries, not implemented behavior. Do not introduce a database, service split, graph engine, or AI dependency in this milestone. Local persistence design follows after serialization and versioning are stable.

## M1.1 — Unified Evidence Schema

1. Write a short contract decision record defining field semantics, supported Python, validation approach, serialization format, versioning, timestamp policy, units policy, and identifier rules. If third-party validation/testing tools are chosen, declare their approved versions and request approval before installation.
2. Define a common envelope: schema version, evidence ID, evidence kind, subject or asset scope using pseudonymous identifiers, event time or interval, ingestion time, source reference, provenance, and quality status with reasons. Define which fields are required for each evidence kind rather than requiring an astronaut for environmental evidence.
3. Define initial observation payloads for physiological and environmental measurements: metric identifier, typed value, explicit unit, and missing/invalid status. Specify mutually consistent value/status combinations and a narrow documented unit vocabulary; reject unknown units unless explicitly represented as unsupported. Numeric validation must reject non-finite values without imposing clinical ranges.
4. Define derived-evidence metadata: input evidence IDs, transformation identifier/version, generation time, and optional method-specific uncertainty. Do not add anomaly, fusion, probability, or recommendation algorithms. Do not default unknown uncertainty to a numeric confidence.
5. Establish deterministic JSON serialization and rejection or explicit handling of unsupported schema versions and unknown fields. Preserve supplied timezone offsets or normalize with documented UTC semantics; reject timezone-naive timestamps. Keep mission time separate from wall-clock time. Validate interval ordering without silently correcting clock anomalies.
6. Add synthetic fixtures and tests for valid physiological/environmental records, missing/invalid readings, invalid units and value types, non-finite numbers, timestamps/offsets, interval ordering, provenance, derived lineage, schema version behavior, and serialization round trips. Mark every fixture synthetic and avoid medical thresholds.

### Acceptance criteria

- Documented and typed contracts import without starting services or accessing a network.
- Valid records serialize and deserialize without losing units, time semantics, status, or provenance.
- Invalid records fail with actionable field-level errors; missingness never becomes zero or normality.
- Source records and derived evidence remain distinguishable; derived records carry input IDs and transformation versions. Referential existence and graph cycle checks are explicitly assigned to later ingestion/storage validation, not falsely guaranteed by a standalone record schema.
- Version policy and representative synthetic examples are documented; tests run offline with approved, pre-provisioned dependencies.
- No clinical thresholds, AI algorithms, database, or HTTP service are required for acceptance.

## Verification and next task

Inventory and Git checks establish that the baseline is a scaffold. Runtime tests cannot validate it because there is no application or executable test content. This assignment adds documentation only.

Recommended next implementation task: approve and implement the M1.1 evidence contract decision record, followed by typed observation/evidence schemas and synthetic validation tests. Resolve the Python target and dependency approach first; obtain approval before installing packages. README/configuration/ignore hardening should accompany the first development setup, before introducing secrets, environments, or generated data.
