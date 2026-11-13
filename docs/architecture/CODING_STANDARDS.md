# CAREYONDA coding standards

## Scope and architectural assessment

CAREYONDA is an offline-first research decision-support platform. The backend is an empty scaffold, not an implemented system. The existing directories offer useful responsibility boundaries; no directory migration or new service is needed now. This policy supplements `AGENTS.md`; its safety, data protection, and change controls remain in force.

Use pragmatic Modular Clean Architecture and SOLID to isolate changes and make behavior testable. These are four logical layers, not a requirement to create four new directory trees. Add an interface or abstraction only when a current caller needs a replaceable boundary. Prefer small functions and composition over inheritance, generic base services, or framework machinery.

## Proposed boundaries within the current layout

| Layer | Current location / intended responsibility | Dependency rule |
| --- | --- | --- |
| Presentation | `app/api`: HTTP parsing, API contracts, response/error mapping | Calls application use cases; no inference or persistence logic in handlers |
| Application | Workflow orchestration when first implemented; `app/ingestion/collector.py` may coordinate ingestion | Calls domain contracts and injected adapter interfaces; never imports concrete storage or model runtimes |
| Domain | Observation/evidence concepts; pure rules in `quality`, `features`, `ai`, and `safety`; reasoning interfaces | No FastAPI, database implementations, frontend code, or runtime I/O |
| Infrastructure | `app/storage`, future acquisition/hardware adapters and model runtime adapters | Implements interfaces owned by domain/application; depends inward |
| Composition root | `app/main.py` and configuration loading in `app/core` | Constructs adapters and use cases and connects HTTP handlers; does not contain business rules |

`app/schemas` initially holds shared versioned external evidence contracts using Pydantic v2. They must remain independent of transport frameworks, storage, and inference implementations. HTTP-only request/response models belong beside the API. Internal domain types can be dataclasses or other simple typed objects; translate at boundaries where representations differ, not mechanically for every object.

The table is a logical assignment, not a claim that existing placeholders implement these roles. Inference algorithms may live in `app/ai`; loading models, files, devices, or vendor libraries belongs in an injected infrastructure adapter. Likewise, pure quality checks are domain behavior while acquisition is infrastructure. Document the location of the first actual application use case when it is needed; obtain approval for substantial reorganization.

Explicit typed functions or small `Protocol` interfaces describe real boundaries. Constructor injection supplies repositories, clocks, data sources, and model adapters where needed. A composition root may import both sides to wire them together; that exception does not permit outward dependencies in domain code. Avoid global mutable state, service locators, import-time I/O, circular imports, and injection frameworks.

## Module responsibilities

| Module | Single responsibility |
| --- | --- |
| `anomaly.py` | Anomaly detection |
| `baseline.py` | Personalized baseline calculation |
| `temporal_fusion.py` | Temporal evidence correlation |
| `knowledge_graph.py` | Hazard relationship queries through explicit contracts |
| `probabilistic.py` | Probabilistic inference |
| `policy_engine.py` | Safety policy evaluation independent of model hypotheses |
| `procedure_registry.py` | Approved procedure lookup and version tracking |
| `explanations.py` | Structured explanation generation from traceable results |

Keep acquisition, transformation, inference, safety decisions, and explanation generation separate. Workflow code coordinates them; it must not become a monolithic implementation. Review functions and classes for one clear purpose, descriptive names, duplication, excessive nesting, and hidden side effects. Do not impose arbitrary file-size limits in place of judgment.

## Python and dependencies

Use Python 3.11 or newer and PEP 8. Target Python 3.11 syntax until the minimum is deliberately changed. Newer interpreters require validation with the selected dependencies; `requires-python` alone does not establish tested compatibility.

`backend/pyproject.toml` is the authoritative initial dependency and tooling declaration: Pydantic v2 for external validation; Ruff, mypy, and pytest for development. The existing empty `requirements.txt` remains a placeholder, not an alternative dependency source. Version ranges are initial compatibility constraints, not a reproducible lock or proof of compatibility. No package installation is authorized by this policy. Before provisioning, approve a resolver/workflow, produce a resolved lock or pinned artifact manifest, and stage dependencies for offline use. Do not add web, database, numerical, or model packages before an implementation needs them.

Use typed public interfaces and strict mypy. Do not introduce blanket `Any`, missing-import suppression, broad excludes, or unchecked casts to make checks pass. Any narrow ignore must identify the error code and explain why. Ruff checks errors, imports, common bug patterns, and Python modernization; its formatter enforces consistent layout. The initial lint rules are intentionally focused, rather than every optional rule. PEP 8 still applies in review beyond automated rules.

## Errors, data, and AI safety

Use meaningful domain exceptions and translate adapter failures at boundaries, preserving causes without leaking sensitive values. Distinguish malformed external input, quality limitations, inference failure, and infrastructure failure. Never silently swallow exceptions or turn failure into normal readings. Safe error categories and pseudonymous correlation IDs belong in logs; health records and secrets do not.

Future AI modules must receive validated versioned inputs and return structured versioned outputs. Preserve source observations, derived-input lineage, timestamps, units, model and transformation versions, missingness, conflicts, and uncertainty. Never equate anomaly scores with clinical probabilities. Separate training from inference and record experiment configuration, artifact versions, seeds, and relevant runtime details; document nondeterministic limits.

Approved safety procedures stay separate from model hypotheses. Do not invent clinical thresholds or medical actions. Models cannot override safety policies or initiate autonomous medical/flight-control actions. Core execution and tests must work offline, without runtime downloads, mandatory cloud dependencies, or telemetry.

## Tests and compliance

Every implemented feature needs appropriate tests. Use unit tests for module behavior and integration tests for component interactions. Include positive, negative, boundary, and missing-data cases where relevant. Use synthetic non-identifying fixtures, fixed clocks and seeds where needed, and infrastructure substitutes at application boundaries. Test public behavior rather than private method layout. No application or AI features are implemented by this standards change, so no behavior tests are added for empty placeholders.

Run these commands from the repository root with previously approved tools available in the active environment:

```sh
cd backend
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy
python -m pytest
```

These are check commands; formatting modifications require an intentional edit. mypy checks tests as well as application code. Pytest treats warnings as errors, rejects unknown markers/configuration, and searches only `backend/tests`. Add narrow documented warning exceptions only for demonstrated issues. Tool caches use ignored relative `.ruff_cache`, `.mypy_cache`, and `.pytest_cache` directories so checks work on Linux and Windows without writing to a Unix-only absolute path. Include `../simulator` in the Ruff commands; the configured mypy file list already includes the sibling simulator.

A zero-test pytest run exits with code 5 and is not a passing suite. Empty modules may pass lint/type checks without providing functionality. For each feature, review test coverage of behavior, dependency direction, provenance, safety, and offline operation alongside tool results. Tools alone do not enforce layer boundaries or clinical validity. Introduce automated import-boundary enforcement only when actual code creates a demonstrated need.

For each milestone: read `AGENTS.md`, inspect relevant code, state scope, implement the smallest maintainable change, add tests, run checks, review staged and unstaged diffs (including new files), and report results and limitations. Document any unavailable checks rather than implying success. Do not commit, push, delete, or substantially reorganize without approval.

## Next implementation task

M1.1 should define the evidence contract and implement only schemas with synthetic validation tests. This policy selects Pydantic v2 and the development tools; dependency installation and a reproducible offline provisioning workflow remain pending. README setup instructions, ignore protection, and runtime configuration remain incomplete. No AI modules should be implemented yet.
