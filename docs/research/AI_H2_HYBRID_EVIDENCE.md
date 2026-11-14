# AI-H2 hybrid evidence reasoning

Research only; offline, deterministic Python 3.11+. This milestone builds on
AI-H1 commit `f0413d8ca97d1ce95e008e58d7cdbd32fca4dc3f` in the isolated
`CAREYONDA-ai-hybrid` worktree. No existing M2, AI-H1, M4.2, model algorithm,
safety policy, API, frontend, dependency or persistence format is changed.

## Interface and interpretation

```python
from app.ai.research.hybrid import evaluate_hybrid_evidence

assessment = evaluate_hybrid_evidence(
    investigation, temporal_summary,
    policy=hybrid_policy,
    assessed_at=aware_assessment_time,
    m2_evidence=original_research_evidence,
    model_contexts=(),
)
```

The result is `app.schemas.hybrid.HybridAssessment`. Evaluation addresses **one
existing M2 hypothesis**, selected by `HybridPolicy.hypothesis_id`. It preserves
the entire original investigation, engine version, rankings, compatibility,
uncertainty and safety status. Its SHA-256 binds the exact serialized M2 snapshot;
the digest provides content integrity, not source authentication. No new hypothesis
catalogue, ranking, probabilities, medical confidence or action is produced.

`m2_evidence` is required because M2 IDs alone lack mission/subject/source and
availability information. Inputs reuse M4.2 `ResearchEvidence`, M1 observations,
canonical units, original provenance, UTC time types, and `SourceRequirement`.
Original M2 findings are verified against their referenced observations before
association. Numeric means and empirical reference extrema must match M2's declared
values and relation exactly; boolean/categorical state relations must match the
source state. This is consistency verification, not a modified M2 ranking algorithm.

`HybridPolicy` is a versioned research-only snapshot. Each unique metric rule has
an ID, version, explicit caller-supplied reference, exact source requirement,
expected M2 relation, minimum count, and explicitly permitted temporal patterns.
It must match the original hypothesis's declared expectation. Rules are research
assumptions, not approved medical procedures. Unconfigured expected metrics remain
missing; a caller cannot omit an inconvenient indicator and obtain full support.
At least one rule must require a temporal pattern. No medical or association
thresholds are supplied by default.

AI-H1 is independently reconstructed from its original supporting/excluded evidence
and sidecars. A structurally valid but unreproducible temporal summary raises
`HybridInputError`. The temporal rule additionally requires exact scope, source,
M2 event window and eligible lineage; stale summaries or future assessments cannot
supply usable evidence. Temporal bounds remain caller statistical conventions;
M2 empirical comparisons and AI-H1 bands are never silently equated.

## Association and output

Every contributing observation requires exact mission and subject/environment
scope, dataset/run, source, sensor/epoch, origin, metric, canonical unit, evaluated
valid quality, bounded complete event support, known prospective availability and
fresh current/reference evidence. Reference freshness uses a separate explicit
maximum age. M1 physical-domain quality checks are applied even when AI-H1's source
quality label says valid. Derived observations with unresolved ancestry are
quarantined; parent IDs alone do not authenticate provenance.

Repeated IDs within supplied M2 evidence or findings, conflicting snapshots shared
between M2 and AI-H1, simultaneous readings, unbound IDs and disagreements between
M2 values/relations and snapshots are quarantined. Exact snapshots shared across
M2 and AI-H1 are references to the same evidence, never independent votes.
Unassociated extra records are retained and explicitly excluded. Input evidence
order does not change results. Malformed contracts, missing/ambiguous hypothesis
identity, overlapping M2 reference/current windows and invalid policy metrics raise
validation or `HybridInputError`; well-formed unavailable evidence is reported in
an abstaining assessment.

The output contains:

- Original investigation snapshot/digest and hypothesis ID, policy and UTC assessment.
- Original AI-H1 summary and considered research-evidence snapshots.
- Supporting and contradicting observation IDs, missing expected metrics and
  unavailable/incompatible evidence with reason codes.
- Per-metric claim, original expected and observed relation, considered current and
  reference IDs, rule ID, temporal pattern/window, verdict, reasons and explanation.
- Original model contexts and digest-linked model association traces.
- Explicit limitations and abstention reasons. Raw, derived temporal and model
  evidence remain distinguishable through their nested contracts and trace roles.

Research statuses describe association with **descriptive M2 expectations**, not
medical truth:

| Status | Deterministic meaning |
| --- | --- |
| `supported_by_available_evidence` | All configured M2 expectations resolved, with support and no contradiction or missing expectation. |
| `contradicted_by_available_evidence` | All expectations resolved, with contradiction and no support. This does not establish hazard absence. |
| `mixed_evidence` | Both directions are present; missing/excluded evidence remains visible. No single direction is selected. |
| `incompatible_evidence` | Incompatible input blocks an expectation, without overriding a visible mixed result. |
| `insufficient_evidence` | Missing, unavailable, stale or ineligible evidence prevents complete association. |

Directional IDs can remain visible in an insufficient/incompatible result; they
only support their individual metric expectations. Abstention reasons accompany
those two statuses. A mixed status reports explicit conflict rather than selecting
a hypothesis. Clinical recovery is never inferred from AI-H1's `recovery` label.

## Model and scientific limitations

Model A `EnvironmentalAnomalyContext` snapshots retain identity/hashes, source
observations/features, imputation, original times, replay metadata, abstentions
and limitations. Flags are always `cannot_establish` in hazard-direction traces.
They provide descriptive statistical context, not causal or faithful feature
attribution. A not-flagged result never supplies health, safety or hazard-absence
evidence. Optional abstentions do not negate independently resolved measurements;
`require_model_context=True` explicitly abstains without an eligible context.
Conflicting sidecars with the same sample/assessment identity are quarantined;
identical shared sidecars are one provenance record.

This release deliberately supports **exact scope only**. It does not implement
subject/environment exposure associations or cross-sensor/unit conversions.
Model A's RR-1 spacecraft CO2 concentration and M2's CO2 partial pressure plus
astronaut observations lack a verified common source/subject interface in this
baseline. Therefore these Model A sidecars cannot establish hazard-specific
support here. Historical replay is explicitly excluded from prospective
association, including synthetic astronaut/replay mixtures. A genuine future
cross-scope association needs a separately reviewed contract and availability,
location, common-origin and provenance evidence. Inventing a link is not a fallback.

No Model B inference contract/implementation is present in this worktree.
M4.2 `AnomalyFinding` remains a declaration contract, not an implemented Model B
adapter. AI-H2 does not consume unverified objects or generic LLM output. The
engine is a conservative rule evaluator, not multimodel clinical validation.
Availability and supplied evidence completeness remain caller declarations.

## Reproducible comparison and evaluation

From `backend`, using already provisioned dependencies:

```sh
PYTHONPATH=. python -m examples.hybrid_evidence
PYTHONPATH=. python -m examples.hybrid_research_cases
python -m pytest tests/unit/test_hybrid_evidence.py tests/integration/test_hybrid_research.py -q
python -m pytest -q
python -m ruff check app tests examples
python -m ruff format --check app tests examples
python -m mypy --explicit-package-bases
```

The example compares original M2 status/ranks, the unmodified M2 result with an
AI-H1 temporal sidecar, and AI-H2's separate assessment. The independently authored
case oracle hardcodes expected statuses and directional observation sets from the
synthetic case definitions, never from evaluator outputs. Cases A–J cover persistent
support, isolated spikes, conflicting indicators, missing/stale readings, different
subjects, replay mismatch, model abstention, future availability, duplicate
provenance and statistical return. An additional all-contradicting case exercises
the negative status. All numbers and model contexts are generated fixtures;
artificial context scores are declarations for software tests, not fitted outputs.

The checked-in `AI_H2_SYNTHETIC_EVALUATION.json` records finite-case software
measurements. Association correctness compares exact status and both directional
ID sets against the oracle. Unsupported assertions count unexpected directional
ID assignments, not clinical assertions or model calibration. Contradiction
handling compares contradictory sets in the two conflict cases. Abstention checks
the eight independently expected blocked cases. Trace completeness resolves
current/reference IDs to original snapshots; tests also verify source, quality,
availability and rule references. Determinism compares complete serialized output
under reversed evidence ordering.

These controlled software checks do not estimate clinical/operational accuracy,
causality, generalization or calibrated uncertainty. There is no NASA data,
training, fitted artifact, network access or new dependency in this milestone.

Next recommended task: cross-model research evaluation after verifying the actual
Model B interface and reviewing genuine common-context association evidence.
Keep all comparisons as sidecars; review fixture-independent cases and temporal
coverage requirements before enabling additional evidence associations.

## Verification record — 2026-11-14

- Focused AI-H2 tests: **69 passed** (unit and integration).
- Full backend suite: **548 passed, 2 skipped** in 4.58 seconds. Skips require
  explicit trusted local fitted artifacts or NASA CSVs; none is added to Git.
- Ruff lint passed for app/tests/examples; all 83 Python files passed formatting.
- Strict mypy passed its configured 83-file scope and explicit eight-file AI-H2
  scope. Python 3.12.10 reused the provisioned Model A environment; existing Ruff
  and mypy executables were reused with `--python-executable` pointing to it.
- Both runnable examples passed. The JSON comparison records 12/12 association
  cases, zero unexpected directional assignments, 2/2 contradiction cases,
  8/8 expected abstentions, 40/40 current and 18/18 reference links resolved,
  and 12/12 deterministic serialized outputs under reversed input order.
- Original M2 rankings/snapshots remain byte-identical in all controlled cases.
  Existing tracked files are unchanged relative to AI-H1. No installation,
  runtime integration, retraining, main-branch change, push or merge occurred.
