# Model C — Isolation & Confinement longitudinal research monitor

Date: 2026-11-14. Branch: `feature/omar-model-c`, based on `origin/feature/model-a-integration` at `1ebdd03`, a fast-forward of the previously empty `origin/feature/omar-model-c` at `bdb29e5`. Status: **research prototype; published implementation with P0 reliability remediation.** The `instrument_kind` contract change (§8) was approved by the project owner on 2026-11-14; the overall implementation still awaits review.

Model C compares a single crew member's supported behavioural indicators with **that same person's own earlier reference period**. It is research decision support only. It does **not** diagnose depression, anxiety, sleep disorders or any other condition. It does not prescribe treatment or operational action, does not infer causes (including isolation or confinement themselves), and produces no risk, severity or composite score.

## 1. What the repository actually supports

Indicators were chosen from the Observation v1 `METRIC_REGISTRY` (astronaut scope), not from domain literature.

| Indicator | Registry definition | Used by Model C | Reporting nature |
| --- | --- | --- | --- |
| `sleep_duration` | behavioral, numeric, unit `h` | **Yes** — numeric personal baseline | Not declared by any contract; each record's provenance (`measured` / `self_reported` / `derived` / `simulated`) is reported |
| `fatigue_self_report` | behavioral, categorical `rested` / `tired` / `very_tired` | **Yes** — descriptive category counts | Self-report by metric definition; provenance also reported |
| `sleep_state` | behavioral, categorical `awake` / `asleep` | No | No producer or data exists in the repository |
| `heart_rate` | physiological, numeric `bpm` | No | Not an isolation/confinement indicator in any contract; strongly confounded by `exercise_active`; no resting-heart-rate contract |
| `exercise_active`, `communication_delay` | mission context | No | Context only; using them would imply unsupported causal links |
| Mood, stress, social interaction, journals, cognitive tests | — | **No** | **No contract, field or data source exists.** None was invented. |

Not used: NASA RR-1 environmental data (environment only, not paired with any astronaut), radiation, and any free text.

## 2. Contracts

New module `backend/app/schemas/isolation_confinement.py` (request/result schema `1.0.0`, model version `1.1.0`, `interpretation="research_only"`). Version 1.1.0 added `IndicatorSource.instrument_kind` (`sensor` | `self_report_form`); see §8.

| Contract | Purpose |
| --- | --- |
| `ModelCRequest` | One subject, mission, dataset/run and data origin; explicit `reference_interval`, `assessment_interval`, `assessed_at`; one `IndicatorSource` per indicator (exact source, sensor, epoch); `ModelCParameters`; optional M4.2 `AnomalyPolicy`; `ResearchEvidence` records. Rejects evidence from another subject/mission/dataset/run/origin, mixed real and synthetic origins, undeclared metrics, overlapping or misordered periods, and threshold approval after assessment. |
| `ModelCParameters` | Every statistical parameter explicitly, with `parameter_status` `unvalidated_research_default` or `caller_supplied`. |
| `NumericIndicatorAssessment` | Embeds the M4.2 `BaselineProfile` and one M4.2 `AnomalyFinding` per assessment-period reading, plus a reconciled `FindingSummary`. |
| `CategoricalIndicatorAssessment` | Registry-ordered category counts for both periods, report lineage, and excluded records with reasons. |
| `IsolationConfinementAssessment` | Per-indicator results, `status` = `assessed` / `partially_assessed` / `abstained`, deterministic `assessment_id`, model/method versions, parameters snapshot, unused evidence IDs, `safety_status="not_evaluated"` and mandatory limitations. **No overall score field exists.** |

Existing contracts (Observation v1, M4.2 baseline/anomaly) are reused unchanged. Their validators independently re-check every count, bin, span, gap, median/MAD relationship, deviation, score and threshold decision that Model C declares.

## 3. Method (`model-c-bin-median-raw-mad-1.0.0`)

### `sleep_duration` — personal numeric baseline

1. **Partition.** Readings whose event time falls in `(reference start, reference end]` are reference candidates. Readings in `(assessment start, assessment end]` are assessment targets. Anything else is listed in `unused_evidence_ids`.
2. **Reference inclusion.** A reference reading is included only if:
   - it has valid quality and a numeric measurement;
   - its source, sensor and epoch exactly match the declared source;
   - its temporal support lies within the reference period;
   - it was available at assessment time (in prospective mode, `ingested_at ≤ assessed_at`).

   Otherwise it is excluded with explicit reason codes (`quality_missing`, `measurement_unavailable`, `source_or_sensor_mismatch`, `support_outside_reference`, `unavailable_at_assessment`). Different simultaneous readings are all excluded as `conflicting_simultaneous_readings`.
3. **Binning.** The reference period is split into bins of `bin_duration_seconds` (M4.2 half-open bins). Each occupied bin is summarised by the median of its readings.
4. **Reference statistics.** `median_value` is the median of the bin medians, and `raw_mad` is the median of |bin median − `median_value`|, unscaled. Bins give each day equal weight however often it was sampled.
5. **Coverage gate** (M4.2 semantics). The profile is `insufficient_reference`, with no statistics published, if any of these fails: occupied bins, observed span, occupancy fraction, maximum gap or reference age. It is `unsupported` when no sensor identity is declared, and `flat_reference` when `raw_mad = 0`. **No epsilon is ever added.**
6. **Findings.** Each assessment-period reading gets an M4.2 `AnomalyFinding`:
   - **`scored`** (ready baseline, valid reading): `raw_mad_score = |value − median| / raw_mad`. This is dimensionless; **not a z-score, probability or severity**.
   - **`flat_reference`:** the deviation is reported, with no score.
   - **`invalid_observation`:** suspect or invalid quality; the original value is kept.
   - **`unsupported`:** missing or unavailable value, source mismatch, late availability or unknown sensor.
   - **`insufficient_reference`:** the baseline could not be used.

   `threshold_status` stays **`unassessed`** unless the caller supplies an M4.2 `AnomalyPolicy` with `approved_research` governance, a calibration artifact and a threshold approved no later than assessment.
7. **Indicator status.** `assessed` only with a ready baseline and at least one scored reading; otherwise `abstained`, with reasons.

### `fatigue_self_report` — descriptive counts only

Valid categorical reports from the declared source are counted per registry category in each period; other reports are excluded with reasons. The indicator abstains if:

- the reference period has fewer than `minimum_reference_reports` reports;
- the assessment period has none;
- the reference is older than allowed.

**No score, distance, test statistic or threshold is computed.** Categories are ordinal labels, but Model C does not assign them numeric values.

### Explanations

Deterministic text names the indicator, both periods (UTC), the reference median and raw MAD (numeric) or counts (categorical), how many readings moved above or below the personal median, and every abstention reason.

## 4. Research parameters (configurable, not validated)

`DEFAULT_RESEARCH_PARAMETERS` in `app/ai/isolation_confinement.py` has `parameter_status="unvalidated_research_default"`. These are software defaults for daily records, **not clinical, NASA-approved or operational limits**:

| Parameter | Default | Note |
| --- | --- | --- |
| `bin_duration_seconds` | 86 400 (1 day) | One bin per day |
| `minimum_occupied_bins` | 7 | Must fit the reference period |
| `minimum_observed_span_seconds` | 6 days | — |
| `minimum_occupancy_fraction` | 0.5 | Occupied / total bins |
| `maximum_gap_seconds` | 3 days | Between consecutive included readings |
| `maximum_reference_age_seconds` | 7 days | Measured from reference end to assessment time (M4.2), so it must cover the assessment period |
| `minimum_reference_reports` | 7 | Categorical indicator only |
| `availability_mode` | `retrospective` | `prospective` enforces ingestion-time availability |

## 5. How to run

The pure Python entry point accepts validated evidence; the optional local HTTP route is described in §8. From `backend/` with the project interpreter:

```python
from app.ai.isolation_confinement import (
    DEFAULT_RESEARCH_PARAMETERS,
    assess_isolation_confinement,
)
from app.schemas.isolation_confinement import ModelCRequest

request = ModelCRequest.model_validate(payload)  # ResearchEvidence for ONE subject
result = assess_isolation_confinement(request)   # pure, deterministic, no I/O
print(result.model_dump_json(indent=2))
```

`tests/unit/test_isolation_confinement.py` contains complete synthetic payload builders.

Tests: `python -m pytest tests/unit/test_isolation_confinement.py`. If FastAPI/Starlette are not installed, this branch's `pyproject.toml` warning filter refers to a Starlette class and pytest cannot start. In that environment, add `-o filterwarnings=error`, which keeps warnings-as-errors and only drops the Starlette-specific ignore.

## 6. Data availability and limitations

- **No longitudinal per-subject data exists in the repository.** Simulator episodes are 30 one-minute steps for one fictional crew identity reused across missions. They must not be pooled into a personal history, and they are far too short for day-level baselines. The API fixture has 145 observations across 4 short presets. All Model C tests therefore use synthetic multi-day series built in the test file.
- No real astronaut data, and no approved research threshold or calibration artifact, exist. Threshold decisions are therefore `unassessed` by default.
- The temporal support of each record (for example the sleep period that a `sleep_duration` summarises) is a caller declaration. Model C does not verify it.
- Median/MAD with daily bins is a simple, transparent research choice. It has not been scientifically validated for spaceflight behavioural monitoring.
- Change relative to the personal reference is not evidence of cause. Sleep and self-reported fatigue are affected by many factors (schedule, workload, illness, exercise, environment) that Model C does not observe.
- Indicators are never combined. Two indicators moving together does not raise any combined signal.
- Passing tests establishes software behaviour only, not medical or operational suitability.

## 7. Integration boundaries (not implemented — need separate approval)

| Boundary | Status |
| --- | --- |
| HTTP API | Local route only: `POST /api/v1/model-c/local-assessments`, mounted by the separate composition root `app.model_c_main`. The base synthetic-only `app.main` is unchanged and does not expose it (§8). |
| `EvidenceSource` / fixtures | Not used. Current presets return `Observation`s without the `ResearchEvidence` declarations (dataset, run, sensor, epoch, temporal support) that Model C requires. |
| Database | Not touched. The `feature/database` design already proposes `research_records` / `research_record_evidence` for M4.2 profiles and findings; a Model C assessment kind would be added there after review. |
| Frontend | `/model-c` page for transient manual self-reports (§8). App routing, the navigation list and one App test condition (`!m.local`) were updated; no other page changed. |
| M2, Model A, Model B, safety policy | Not modified or consumed. `ai/baseline.py` and `ai/anomaly.py` are left empty because the Model B branch uses those paths. |

## 8. Local self-report entry flow (model 1.1.0)

Lets a person type daily values for **one pseudonymous participant**, submit the history once to the local backend, and read the actual Model C result. This is a **local demonstration**, not operational astronaut monitoring and not a diagnostic tool.

### Contract change (versioned, minimal) — approved by the project owner, 2026-11-14

M4.2 allows a `ready` personal baseline only with `exact_identity` source matching, which requires a declared `sensor_id`/`sensor_epoch`. Manually typed self-reports have no sensor, so without a change they could only ever abstain as `unsupported`. Inventing a device ID would misrepresent them.

Model 1.1.0 therefore adds `IndicatorSource.instrument_kind`:

- `sensor`: `sensor_id`/`sensor_epoch` is the device identity, which may be undeclared (then `unsupported`). Evidence may carry `measured`, `derived` or `simulated` provenance — never `self_reported`.
- `self_report_form`: `sensor_id`/`sensor_epoch` is **the entry form's identifier and version** (`model-c-local-entry-form` / `form-1.0.0`), the real instrument. It sits in the M4.2 sensor slot only so that exact matching applies to the same form version. Evidence must carry `self_reported` (or `simulated`) provenance. Every result repeats `instrument_kind`, and every explanation states "no physical sensor is involved".
- `fatigue_self_report` must use a `self_report_form`.

M4.2 contracts and Observation v1 are unchanged.

### Request and time convention

`ModelCLocalSubmission` (`backend/app/schemas/model_c_local_entry.py`, schema `1.0.0`):

| Field | Rule |
| --- | --- |
| `participant_id` | Pseudonym `^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$`; rejects e-mail addresses and names containing spaces. It cannot prove anonymity, so the UI asks for a pseudonym. |
| `assessment_days` | 1–7; the most recent dated entries form the assessment period |
| `entries` | 1–60, unique dates |
| `entries[].date` | `YYYY-MM-DD` text only; no epochs, times or impossible dates |
| `entries[].sleep_duration_hours` | Optional JSON number, 0–24 (bound of the 24-hour support window; not a clinical range) |
| `entries[].fatigue` | Optional `rested` / `tired` / `very_tired` |

Unknown fields (for example mood) are rejected, and an entry with neither value is rejected.

**Time convention (declared, not measured):** an entry dated D is a report at 12:00 UTC on D. Sleep covers (D−1 12:00, D 12:00] UTC; fatigue is a point report at 12:00 UTC.

- Entries whose report time is after the server's receipt time are refused (`entry_after_report_time`).
- The reference period is all earlier dates. It is declared at least as long as the research parameters require, so a short history yields an explicit `insufficient_reference` abstention rather than an input error.
- A blank field becomes an explicit `unavailable` / `not_collected` record with reason `not_entered`. It shows up as an exclusion or an unsupported finding, **never as zero**.
- All records have `self_reported` provenance, `crew_report` source type and `real` data origin. They are never labelled synthetic or sensor data.
- The mission is labelled `no-mission-declared`, because a manual entry declares none.

### Backend

- `app/application/model_c_local.py`: a pure translation into a `ModelCRequest`, then Model C. No I/O, logging or state; tests check its imports.
- `app/api/model_c.py`: `POST /api/v1/model-c/local-assessments` returns `ModelCLocalResponse` with `source="transient_local_self_report"`, `persistence="none"`, the time convention and the full result. Errors return only a safe code and the correlation ID, never values. The existing `RequestGuard` limits apply: loopback host, 16 KiB body, JSON only.
- `app/model_c_main.py`: optional composition root (base app plus this route). Run it with `uvicorn app.model_c_main:create_app --factory --host 127.0.0.1`.

### Frontend (`/model-c`, "Isolation & Confinement · Model C")

- **Session:** the participant ID locks once a day is added; "Clear session" discards all entries, so two participants are never mixed.
- **Entry:** date (UTC), sleep hours and fatigue per row, with "Add day" and remove. Client-side validation mirrors the server, which stays authoritative.
- **Submission:** only in "Local API" mode. Fixture mode never runs Model C and never fabricates a result.
- **Results:** status, abstention reasons in plain words plus their codes, reference and assessment periods, assessed time, parameters (labelled unvalidated research defaults), baseline median and raw MAD with day coverage, per-entry differences and scores with their meaning, exclusions, fatigue counts, instrument and provenance, the time convention, and all limitations.
- **Nothing is persisted:** state lives in React memory only. There is no localStorage, sessionStorage, IndexedDB, cookies, analytics or third-party request. The single request uses `credentials: "omit"`, `cache: "no-store"` and a loopback-only origin.

### Run locally (PowerShell, from the repository root)

```powershell
# Backend: worktree-local venv from the repository pins; serves 127.0.0.1:8000 only
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r backend\requirements-model-a-integration.txt
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.model_c_main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

```powershell
# Frontend (second terminal; requires Node >=22.12 <25, per package.json engines)
Set-Location frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/model-c`, switch the header data mode to **Local API · synthetic**, enter a pseudonym and dated days, then submit. `VITE_API_URL` (default `http://127.0.0.1:8000`) must point at the backend above.

### Verification status (2026-11-14)

- **Backend (worktree venv from the repository pins, unmodified config):** Ruff lint and format pass; strict mypy passes on 82 files; pytest gives 491 passed and 2 skipped (local NASA-data opt-ins), including the Model C HTTP route tests.
- **Frontend (Node 24.22.3 from the official ZIP, SHA-256 verified, worktree-local; `npm ci` from the committed lockfile):** `npm run typecheck` passes; `npm test` gives 133 passed and 1 skipped (pre-existing Model A local opt-in); `npm run format:check` passes on the LF content Git stores. In a Windows checkout with `core.autocrlf=true`, Prettier's default `endOfLine: "lf"` flags CRLF working copies; that is a line-ending artifact, not a style issue. No lint script is defined.
- **End to end (local servers, built-in browser, synthetic participants only):** a 17-day history with one blank sleep day was assessed, and the blank day was excluded with reasons rather than zeroed. A 3-day history abstained with every coverage reason and no fabricated statistics. Invalid sleep values, empty days and a future date were refused before any request. Only `127.0.0.1` requests were made; browser storage, cookies, IndexedDB and service workers stayed empty; the server logged no entry values.

## P0 reliability remediation

Numeric targets now require ordered temporal support wholly within the declared
assessment period (exclusive start, inclusive end), with support end no later
than `assessed_at`. This check is independent of prospective/retrospective
availability. Support crossing the reference period, outside the assessment
window or after assessment produces an unsupported finding with
`target_support_outside_assessment`, without a score/deviation/threshold decision.
Reversed intervals are rejected by the existing input contract. M4.2 schemas,
median/raw-MAD calculations, thresholds and model version remain unchanged.

The manual-entry UI uses request generations. Clear session, participant/input
changes, row addition/removal, assessment-period changes, API configuration/mode
changes and unmount invalidate earlier requests. Earlier success/error/finally
handlers cannot update the current session or clear a newer request's loading
state. This discards late responses; it does not cancel work already accepted by
the backend. No persistence or frontend redesign is introduced.

Regressions include future and reference-overlapping support in both availability
modes, reversed interval ordering, deferred A → Clear → B → A-response behavior,
all editable inputs, mode changes, stale errors and a newer request's loading
state. All test values are artificial; these fixes establish software temporal
and session isolation, not isolation/confinement or behavioral-health validity.

Remediation verification (Python 3.12.10, existing repository-pinned packages):
79 focused backend tests passed; full backend 498 passed, 2 expected local-data
skips. Frontend Model C 35 passed; full frontend 142 passed, 1 expected local
Model A smoke skip. Ruff lint/format, strict mypy (82 files), TypeScript,
Prettier, production build and dependency/whitespace checks passed. The build
retains two upstream nonfatal Zod annotation warnings. No new packages were
installed; already provisioned dependencies were reused in isolated temporary
copies. No real artifact or NASA measurement was loaded for these regressions.
