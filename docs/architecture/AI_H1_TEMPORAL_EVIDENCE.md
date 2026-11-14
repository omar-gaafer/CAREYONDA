# AI-H1 temporal evidence intelligence

Research only. Python 3.11+; verified using provisioned Python 3.12.10 and the
repository's existing dependencies. No inference service, API, persistence,
training, runtime download, or external data is introduced. Base:
`1ebdd03a8b29239742074e3ac0bff247d8a5785b`.

## Public interface and contracts

```python
from app.ai.temporal_evidence import analyze_temporal_evidence

summary = analyze_temporal_evidence(
    evidence,                 # Sequence[ResearchEvidence]
    policy=policy,            # TemporalPolicy
    assessed_at=assessment,   # aware datetime, normalized to UTC
    model_contexts=(),        # optional existing Model A sidecars
)                             # -> TemporalSummary
```

`app.schemas.temporal` adds independent versioned `TemporalPolicy` and
`TemporalSummary` contracts, plus `ModelContextEvidence`. Existing contracts are
unchanged. The policy snapshot contains subject/mission/location scope, exact
source identity, metric, canonical unit, event window, statistical bounds, count,
run, gap, freshness and slope parameters, research direction, and a caller-supplied
convention reference. All parameters are explicit; none supplies a clinical rule.
`minimum_slope_per_second` is in canonical measurement units per event second.
Policy and summary require schema `1.0.0` and `research_only`; method version is
`temporal-evidence-1.0.0`.

Summary includes ordered observation IDs, original supporting snapshots, excluded
snapshots with reasons, original model sidecars/provenance, UTC assessment and
event span, valid count, span seconds, optional measured slope, missing/unavailable
evidence codes, quality limitations and abstention reasons. Scope is available as
`summary.policy.scope`; source and configuration provenance remain in the policy.
Abstentions publish no slope. Counts describe eligible records, not independent
samples or clinical evidence strength. A stale sequence may retain valid source
snapshots for review while abstaining from classification.

## Contract review and compatibility

- M1 `Observation`, canonical-unit validation, quality and original provenance are
  reused. No implicit conversions or replacement of source observations occur.
- M2 `EvidenceFinding` and `Investigation` describe reference-window hypothesis
  reasoning; they cannot express these sequences without changing their meaning.
  They remain untouched and are not imported by the analyzer.
- M4.2 `ResearchEvidence`, `ResearchTime`, `TimeInterval`, `ExcludedEvidence` and
  research scalar types are reused, as is `fusion.SourceRequirement`. The existing
  `TemporalEvidenceGroup` is a cross-source alignment declaration, not a measured
  trend summary; AI-H1 does not implement or alter its join semantics.
- Model A `EnvironmentalAnomalyContext` is retained intact, including identity,
  hashes, original features, imputation, availability, limitations and abstentions.
  Multivariate sample flags never become per-metric anomaly labels. Context is
  marked `used` only as contextual provenance after exact spacecraft/dataset/run/
  origin, target-observation snapshot, window, freshness and availability checks.
  It never changes the numeric temporal pattern. Astronaut attribution and
  historical replay contexts are excluded explicitly. No subject/environment
  association or causal exposure is inferred.
- Existing artificial environmental fixtures exercise Model A integration without
  NASA data or fitted artifacts. The standalone example supplies explicitly
  simulated astronaut observations with synthetic dataset, run and sensor identity.

## Deterministic semantics

Analyze one exact source, metric and scope per call. Inputs are revalidated,
ordered by `(event time, observation ID)`, and never mutated. Duplicate observation
IDs raise `TemporalInputError`, including identical copies. Distinct IDs at the
same event time are all excluded and force abstention to avoid inflated counts or
arbitrary conflict resolution.

Events and their complete support must fit `(window.start, window.end]`.
Assessment must follow the window end. Every included observation requires known
`ingested_at <= assessed_at` and support ending by assessment. Future/unknown
availability and out-of-window or mismatched evidence are retained as exclusions;
they do not influence values, patterns or counts. Available matching non-valid
readings force abstention rather than allowing a sequence to bridge them.
Insufficient count, excessive gaps (including window edges), stale latest evidence,
unknown source compatibility, and nonfinite arithmetic force explicit abstention.
There is no interpolation, imputation, resampling, cadence inference or assumption
that missing readings are within reference. Availability is declared, not authenticated;
coverage cannot establish that a caller supplied every source record.

Single-label precedence after eligibility/coverage checks:

1. **Recovery**: anomalous prefix of at least `minimum_run` followed entirely by
   at least `minimum_run` readings inside the configured inclusive reference band.
   This means a statistical return to that band, never physiological recovery.
2. **Persistent anomaly**: any consecutive out-of-band run reaches `minimum_run`.
3. **Isolated spike**: exactly one out-of-band point, with in-band evidence on both
   sides. Either upper or lower excursions qualify.
4. **Worsening / improving**: all successive changes have the same sign (ties
   permitted), and absolute endpoint slope reaches the configured minimum.
   The label follows the explicitly configured higher/lower research convention.
5. **No pattern**: sufficient eligible coverage without a supported pattern.
   This does not establish normality or safety.

Bounds, freshness, gap and slope comparisons are inclusive. Precedence means an
out-of-band monotonic series can be labeled persistent rather than worsening;
this release does not emit multiple patterns. No model probabilities, clinical
confidence, diagnosis, hazard severity, clinical thresholds or actions are emitted.

## Example and verification

From `backend`, with existing dependencies available:

```sh
PYTHONPATH=. python examples/temporal_evidence.py
python -m pytest tests/unit/test_temporal_evidence.py tests/integration/test_temporal_model_context.py -q
python -m pytest -q
python -m ruff check app tests examples
python -m ruff format --check app tests examples
python -m mypy --explicit-package-bases
python -m mypy --explicit-package-bases app/schemas/temporal.py app/ai/temporal_evidence.py examples/temporal_evidence.py tests/unit/test_temporal_evidence.py tests/integration/test_temporal_model_context.py
```

The executable example returns `isolated_spike` using arbitrary synthetic values.
`--explicit-package-bases` allows the example's namespace package to be imported by
its tests without duplicate mypy module identities. Verification reused the existing
Python 3.12 Model A environment and existing Ruff/mypy tools; mypy used
`--python-executable` to inspect that environment. No packages were installed.
The full suite's local NASA CSV and trusted fitted-artifact replay tests require
explicit local opt-in and remain skipped; synthetic regressions run offline.
Software checks do not establish medical or operational suitability.

Next recommended task: **hybrid evidence reasoning**, with separately approved
cross-source associations, conflict handling and human-reviewed evidence policies.
AI-H1 stops at temporal descriptions; no hybrid scoring or ranking is implemented.

Final verification (2026-11-14): 479 tests passed, including 60 AI-H1 unit and
integration tests; two explicit local NASA/artifact tests skipped. Ruff lint and
format checks passed across app/tests/examples. Strict mypy passed the configured
77-file scope and the explicit five-file AI-H1/example scope. The standalone
synthetic example produced `isolated_spike`, five valid observations, and
`research_only`. Full local API tests required execution outside the restrictive
sandbox; the sandboxed attempt stalled and was interrupted, then the complete
suite passed in 4.31 seconds. No tracked baseline files changed.
