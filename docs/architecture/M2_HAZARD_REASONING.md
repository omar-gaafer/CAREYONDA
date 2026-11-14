# M2 — Minimal explainable hazard reasoning

## Scope and integration boundary

Work is limited to `feature/hazard-reasoning`. The M1.1 observation/quality contracts, M1.2 feature extractor, simulator, training exporter, and tooling configuration are reused without modification. No dependency, training, HTTP API, frontend, database, Bayesian network, LLM, clinical rule, or approved procedure is added. No commits, merges, or pushes are part of this milestone.

`app.ai.hazard_reasoning.investigate` is a pure synchronous function taking validated observations, a M1.2 `SampleAnchor`, a separately supplied reference observation collection and anchor, and an optional positive trailing window length (default 300 seconds). It calls the existing `build_features` for both windows. It returns a versioned Pydantic `Investigation` with JSON serialization support. It does not read simulator labels, scenario-bearing provenance, or training CSV labels.

The function is ready to call from a future application/API adapter. That adapter must validate external observations, select/authorize the subject/location context, retrieve and justify an earlier reference, handle input errors, and apply a separate approved safety workflow if one becomes available. No HTTP endpoints or request/persistence adapters are implemented. `ReasoningInputError` reports invalid temporal context or inconsistent reused IDs without exposing measurements; existing feature validation errors reject duplicate IDs and invalid windows. Results are intended for authorized consumers; they contain evidence measurements and should not be blindly logged.

## Empirical reference, not clinical thresholds

A caller must explicitly choose the reference window. The engine does not infer that any supplied reference is physiologically normal or clinically safe. Cross-mission/context comparators are permitted, but results never claim a personalized baseline. Reference appropriateness and source authenticity are caller responsibilities. The reference window must end no later than the exclusive lower boundary of the current window, so current/reference periods do not overlap.

For heart rate, CO2 partial pressure, and sleep duration, compare the **current event-window mean** to the minimum/maximum of evaluated-valid numeric readings in the reference window:

- Greater than empirical maximum: `above_reference`.
- Less than empirical minimum: `below_reference`.
- Otherwise, including equality: `within_reference`.

These comparisons introduce no medical normal ranges, clinical cutoffs, tolerances, alert limits, probabilities, or diagnostic confidence values. The exact empirical envelope deliberately has no tuned margin. Narrow/sparse references and measurement noise can change the ranking; this MVP is not a calibrated anomaly detector. A one-record reference is allowed but provides only a point comparator, not a reliable normal range.

Fatigue uses M1.2's existing encoding: latest `rested` report becomes `rested_reported`, while `tired`/`very_tired` become `fatigue_reported`. Exercise uses the latest valid boolean as `active`/`inactive`. These are reported states, not diagnoses. Communication delay is retained in window lineage and quality reporting but is not used to invent a health relationship.

## Synthetic pattern definitions

| Hypothesis ID | Required supporting relations |
| --- | --- |
| `baseline` | HR, CO2, and sleep within the reference envelope; latest fatigue report rested; exercise inactive |
| `elevated_co2` | CO2 above reference and HR above reference |
| `sleep_deprivation` | Sleep duration below reference and fatigue reported |
| `recent_exercise` | Exercise active and HR above reference |

These are explicitly synthetic pattern assumptions, consistent with the M1.2 generator design. Above-reference CO2 and HR are co-occurring evidence; their correlation does not prove that CO2 caused the HR change. Lower reported sleep duration and fatigue are similarly compatible with a synthetic explanation, not proof of a disorder. Exercise can supply a competing explanation for HR elevation. `baseline` means compatibility with this limited reference pattern, never a statement that the astronaut or spacecraft is safe.

## Evidence, conflicts, ranking, and uncertainty

For each hypothesis, report all expected relations and divide its findings into:

- Supporting: the observed relation matches the explicit expectation.
- Contradictory: a usable observed relation disagrees with the expectation, or simultaneous valid readings conflict.
- Missing: no usable current value, or no usable reference value for a numeric comparison. Existing missing/invalid IDs remain traceable; complete absence has an empty ID list.

All evidence findings retain current observation IDs and, for numeric comparisons, reference IDs, units, current means, empirical bounds, and a deterministic explanation. Latest categorical/boolean evidence cites the selected observation. Current/reference window ID lists retain the full M1.2 feature lineage, including communication-delay and excluded records. `quality_issues` records every evaluated-non-valid observation's window, metric, ID, status, and reason codes, including intermittent dropouts when a feature still has usable values. Missingness is never zero, normality, or safety.

Exact simultaneous disagreement among evaluated-valid records for the same metric/context/time is treated conservatively as `conflicting`, rather than silently accepting M1.2's ID-based latest tie-break. Such conflicts in current or numeric reference evidence prevent selection. Ordinary changes across successive timestamps are not simultaneous conflicts; numeric changes contribute to the mean and state inputs use the latest usable value. Averaging can conceal temporal variation; lead/lag or causal sequencing is outside this MVP.

Compatibility categories:

- `supported`: every required relation matches.
- `partial`: some relations support, others are missing, with no contradiction.
- `mixed`: supporting and contradictory findings coexist.
- `contradicted`: contradictory findings and no supporting findings.
- `insufficient`: no usable findings support or contradict the hypothesis.

Ranking is deterministic, not a probability score: category order is supported, partial, mixed, contradicted, insufficient; within a category, fewer contradictions, fewer missing findings, then more supporting findings come first. Wholly unassessable hypotheses tie regardless of their number of required metrics. Identical substantive keys share competition rank (for example 1, 1, 3); hypothesis ID only stabilizes display order and never breaks a substantive tie for selection. Evidence counts are bookkeeping, not calibrated confidence or independent statistical votes.

Select only a unique fully supported hypothesis. Multiple fully supported hypotheses produce `ambiguous` and no selection, even if display order differs. No fully supported hypothesis produces `insufficient_evidence` (insufficient for selection, which can also mean an unsupported/mixed pattern rather than missing data alone). Any simultaneous evidence conflict produces `conflicting_evidence` and no selection. All result paths include explicit qualitative limitations; no probability, score, diagnosis, or recommended action is returned.

`Investigation` includes contract/engine versions, deterministic bounded investigation ID, sample and reference IDs/timestamps, window length, ranked hypotheses, observed/reference lineage, quality issues, and uncertainty. The investigation ID incorporates anchors, window length, and window evidence IDs. Observation IDs are assumed immutable; content authenticity is not verified. Shared IDs with inconsistent contents across input collections are rejected.

## Temporal and safety behavior

Both windows use the unchanged M1.2 `(anchor_time-window, anchor_time]` event-time logic and exact subject/location matching. Future observations and other mission/crew/cabin evidence cannot contribute. Ingestion ordering is not a feature or ranking input; results retain M1.2's retrospective event-time semantics. Late arrivals may be included if their event time is in the window; this is not an online availability replay.

Inference remains separate from clinical safety. The existing `app/safety` placeholders are untouched; the result explicitly carries `safety_status="not_evaluated"`. No policies, treatments, medical actions, clinical thresholds, autonomous commands, or claims of safety are invented. A downstream adapter must not map a selected hypothesis to an action without separately approved procedures.

## Usage with existing artifacts

Run Python with `PYTHONPATH=backend` from the repository root, using the provisioned backend environment. Existing JSON observations and mapping contexts can be reused directly:

```python
import json
from pathlib import Path

from app.ai.hazard_reasoning import investigate
from app.features.temporal_features import SampleAnchor
from app.schemas.observation import Observation

current = Path("datasets/synthetic/current")
reference = Path("datasets/synthetic/earlier_reference")
observations = [Observation.model_validate(o)
                for o in json.loads((current / "observations.json").read_text())]
reference_observations = [Observation.model_validate(o)
                         for o in json.loads((reference / "observations.json").read_text())]
current_context = json.loads((current / "evidence_mapping.json").read_text())[0]["context"]
reference_context = json.loads((reference / "evidence_mapping.json").read_text())[0]["context"]
# In an application, select a suitable earlier comparator explicitly;
# do not assume the first row of an arbitrary dataset is a normal baseline.
result = investigate(observations, SampleAnchor.model_validate(current_context),
                     reference_observations, SampleAnchor.model_validate(reference_context))
print(result.model_dump_json(indent=2))
```

The earlier reference dataset must have an earlier configured start/anchor; default M1.2 episodes all begin together and cannot be silently repurposed as prior history. The integration test shows an end-to-end simulator/export/reasoning example with an explicit prior reference. Tests may use simulator labels to choose controlled cases and check expectations; the engine itself never consumes those labels.

## Verified examples and limits

Controlled simulator examples use seed 42, one episode per scenario, three samples, zero numeric noise, no dropout, an earlier baseline reference starting at 23:00 UTC on 2026-11-12, and current episodes starting at 00:00 UTC on 2026-11-13. At the final sample:

| Synthetic case | Selected pattern | Traceable explanation |
| --- | --- | --- |
| Baseline | baseline | HR 72 bpm, CO2 50 Pa, sleep 8 h match the empirical reference; fatigue rested and exercise inactive |
| Elevated CO2 | elevated_co2 | CO2 mean 170 Pa and HR mean 90 bpm exceed the reference values; inactive exercise contradicts the exercise alternative |
| Sleep deprivation | sleep_deprivation | Sleep mean 3 h is below reference 8 h and latest fatigue report is tired/very tired |
| Recent exercise | recent_exercise | Exercise active and HR mean above 72 bpm; unchanged CO2 contradicts the CO2 explanation |

These demonstrations are not accuracy estimates. Noisy/missing simulator tests check determinism, traceability, and valid abstention behavior rather than promise classification of every generator label. The M1.2 recent-exercise label persists during recovery, but this minimal rule requires an active exercise observation in its current latest state; it cannot reliably identify recovery after that context expires. No hypothesis catalogue completeness, baseline suitability, clinical generalization, or calibration is established.

## Verification

From `backend`:

```sh
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

Tests cover four clean patterns, supporting/contradictory/missing evidence, fully missing input and reference abstention, intermittent quality limits, invalid physical measurements, conflicting simultaneous current/reference records, competing hypotheses/tied ranks, deterministic serialization and ordering, reference chronology, duplicate-ID inconsistencies, future exclusion, scope isolation, maximum-length IDs, and poisoned simulator provenance labels. Integration tests reuse the actual simulator and JSON exporter, including noisy/dropout runs with multiple seeds. No training pipeline changes are needed.


### Delivery verification

Final checks on Python 3.14.8 using the existing environment: Ruff lint passed; formatting passed for 41 files; strict mypy passed for 41 source files; pytest **172 passed** (143 unchanged M1.1/M1.2 cases, 25 reasoning unit cases, four reasoning integration cases). One initial empty-evidence ranking test revealed artificial ordering by required-metric count; wholly unassessable hypotheses now tie, and the final suite passes. Simultaneous conflicts remain visible even when numeric reference evidence is absent.

Changed files: `backend/app/ai/hazard_reasoning.py`, `backend/app/ai/explanations.py`, `backend/app/schemas/evidence.py`, `backend/app/schemas/investigation.py`, `backend/tests/unit/test_hazard_reasoning.py`, `backend/tests/integration/test_hazard_investigation.py`, and this report. All M1.1/M1.2 implementation files, the training pipeline, and safety modules remain unchanged. Work remains uncommitted on `feature/hazard-reasoning`.

A real serialized excerpt from the controlled elevated-CO2 example above (synthetic evidence only):

```json
{
  "schema_version": "1.0.0",
  "engine_version": "reference-rules-1.0.0",
  "status": "ranked",
  "selected_hypothesis": "elevated_co2",
  "safety_status": "not_evaluated",
  "supporting_evidence": [
    {
      "metric": "cabin_co2_partial_pressure",
      "relation": "above_reference",
      "observation_ids": [
        "8d6bbe749bb57feb563008f0e319aa01-cabin_co2_partial_pressure",
        "9ab4456d1b6c95e5cb8baeb7501818e8-cabin_co2_partial_pressure",
        "131ed92d6e25534f863cf143635c1cd9-cabin_co2_partial_pressure"
      ],
      "reference_observation_ids": [
        "5ece3f99624085586515e5eb21fb2b71-cabin_co2_partial_pressure",
        "c48e1044fe63f4268a3a88332294d71b-cabin_co2_partial_pressure",
        "2227571643fb262d5fda7dd4f062af2c-cabin_co2_partial_pressure"
      ],
      "observed_value": 170.0,
      "unit": "Pa",
      "reference_minimum": 50.0,
      "reference_maximum": 50.0,
      "explanation": "cabin_co2_partial_pressure: window mean is above reference (empirical comparator, not a clinical limit)"
    },
    {
      "metric": "heart_rate",
      "relation": "above_reference",
      "observation_ids": [
        "8d6bbe749bb57feb563008f0e319aa01-heart_rate",
        "9ab4456d1b6c95e5cb8baeb7501818e8-heart_rate",
        "131ed92d6e25534f863cf143635c1cd9-heart_rate"
      ],
      "reference_observation_ids": [
        "5ece3f99624085586515e5eb21fb2b71-heart_rate",
        "c48e1044fe63f4268a3a88332294d71b-heart_rate",
        "2227571643fb262d5fda7dd4f062af2c-heart_rate"
      ],
      "observed_value": 90.0,
      "unit": "bpm",
      "reference_minimum": 72.0,
      "reference_maximum": 72.0,
      "explanation": "heart_rate: window mean is above reference (empirical comparator, not a clinical limit)"
    }
  ]
}
```
