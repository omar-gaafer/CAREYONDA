# M4.2 — Implementation and regression verification

Verified 2026-11-13 on branch `feature/hazard-reasoning`, Python 3.14.8,
using the existing backend virtual environment. Python target remains 3.11+;
Python 3.11 itself was not available/tested in this verification.

## Delivered files

| New file | Purpose |
| --- | --- |
| `backend/app/schemas/baseline.py` | Versioned baseline policy/profile, evidence metadata, source scope, intervals and coverage declarations |
| `backend/app/schemas/anomaly.py` | Versioned anomaly policy/finding, research threshold governance and calibration references |
| `backend/app/schemas/fusion.py` | Versioned fusion policy/group, source requirements and subject/compartment association declarations |
| `backend/tests/unit/test_research_contracts.py` | 84 deterministic synthetic contract and M2 regression cases |
| `docs/architecture/M4_2_RESEARCH_CONTRACTS.md` | Contract decisions, field semantics, scientific limits and future integration boundaries |
| `docs/architecture/M4_2_VERIFICATION_REPORT.md` | This implementation and compatibility report |

No pre-existing file was edited. No packages were installed. No algorithms,
training, transport endpoints, persistence adapters, frontend behavior, datasets,
simulators or external services were implemented or changed. All example observations
and threshold values in the new tests are synthetic; real-origin metadata cases
are also synthetic test declarations, never actual astronaut records.

## Verification results

Commands below ran from `backend/` using existing approved dependencies.

| Command | Final result |
| --- | --- |
| `.venv/bin/python -m pytest tests/unit/test_research_contracts.py -q` | **84 passed**, 0.23 s |
| `.venv/bin/python -m pytest` | **296 passed**, 3.47 s |
| `.venv/bin/python -m ruff check app tests ../simulator` | Passed |
| `.venv/bin/python -m ruff format --check app tests ../simulator` | Passed, 57 files |
| `.venv/bin/python -m mypy` | Strict typing passed, 57 source files |
| `git diff --check` from repository root | Passed |

No required final verification command remained unavailable. Full pytest ran outside
the filesystem sandbox with approval for the established local TestClient thread-
portal limitation; tests used local fixtures and did not require external services.
Formatting/import fixes were restricted to the newly created Python files.

Focused coverage includes JSON round trips for all six contracts, unknown fields and
versions, aware UTC timestamps, explicit/missing policy parameters, positive durations
and bounds, non-finite values, extreme finite duration handling, duplicate/empty IDs,
lineage partition overlap, metric/unit/scope/sensor isolation, reference-bin boundaries,
coverage/count/span/gap reconciliation, sparse and flat-reference abstention, null
scores, target missingness, governance and calibration consistency, threshold equality,
freshness equality, source-age/separation equality, lower-exclusive/upper-inclusive
windows, support intervals, explicit conflicts, subject/compartment associations,
unpaired real/synthetic origins, and prospective missing/late/on-time ingestion.

## Existing work and compatibility

Before edits, the working tree already contained modified README, M2 explanation and
schema files, main API composition and backend configuration, plus untracked M2,
local API/application/storage/test/documentation work and frontend sources. That work
was preserved, including all untracked files. The index had no staged diff and remains
unchanged. No branch switch, staging, commit or push occurred.

A temporary SHA-256 inventory captured **406 pre-existing files** under backend,
frontend, docs, simulator and datasets, excluding environment, build and cache
contents. The final comparison found **zero changed or missing pre-existing files**.
Observation v1, Evidence, Investigation v1, M2 reasoning/explanations, source data and
tooling configuration therefore remain byte-for-byte as found at milestone start.
The six delivered files are additions, not part of that pre-existing-file inventory.

All 212 existing backend tests continue to pass alongside the 84 new cases, including
25 hazard reasoning unit tests, four hazard investigation integration tests and 20
local API tests. The additional M2 regression case checks serialized SHA-256 snapshots
for the four controlled synthetic patterns (baseline, elevated CO2, sleep deprivation,
recent exercise), validates their existing selections and `safety_status=not_evaluated`,
and verifies identical serialization after constructing research sidecar records.
The snapshots were captured from the unchanged M2 implementation. No production
caller imports the new research contracts, so M2 has no new integration path.

## Limits and next task

This milestone validates declarations. It does not estimate reference statistics,
score observations, select/join evidence, authenticate artifacts, verify approval
references, establish source completeness or demonstrate clinical validity.
Source compatibility and association attestations still require trustworthy upstream
metadata. Median/MAD statistical correctness and explanation determinism remain
producer responsibilities for future algorithm tests.

The next separately authorized task is M4.3 baseline estimation against explicit
synthetic research policies, with method-versioned outputs, coverage and abstention
tests. M4.4 scoring and M4.5 temporal grouping remain separate later milestones.
No clinical thresholds, probabilities, diagnoses or autonomous actions are introduced.
