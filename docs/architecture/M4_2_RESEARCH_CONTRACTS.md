# M4.2 — Versioned research contracts

Date: 2026-11-13. Status: contracts implemented; research algorithms unimplemented.
Python support remains 3.11+; verification used the existing Python 3.14.8 environment
and declared Pydantic v2 dependency. No packages or runtime artifacts were added.

## Scope and decisions

The six public contracts are `BaselinePolicy`, `BaselineProfile`, `AnomalyPolicy`,
`AnomalyFinding`, `FusionPolicy`, and `TemporalEvidenceGroup`, in the three new
`app/schemas` modules. Each requires `schema_version="1.0.0"` and
`interpretation="research_only"`. Policies additionally require a semantic
`policy_version`; results require a producer `method_version`. Unknown fields and
unsupported versions are rejected. No schema is imported by the existing M2 engine,
application, persistence adapter, or HTTP routes.

Policy snapshots are nested in results; the anomaly finding also nests its baseline
profile. This deliberately favors independently reviewable offline records over
compact references that would require a registry or network lookup. Policy identity,
reference interval, dataset/run/mission/subject, source/sensor scope and reference
lineage are therefore accessible through the nested snapshot rather than duplicated
fields that could disagree. A finding identifies its target via
`evidence.observation.observation_id` and its profile via `baseline.profile_id`.
No persisted storage format, endpoint, or existing public contract changes.

Small shared research types live in `schemas/baseline.py`; anomaly and fusion depend
on these contracts and Observation v1, never on AI or infrastructure. This introduces
no generic service layer. Helpers check declarations and do not estimate baselines,
produce findings, select/join observations, or generate explanations. Arithmetic
checks of supplied counts, deviations, scores and threshold decisions reject
contradictory declarations; they do not populate result fields.

## Evidence and provenance

`ResearchEvidence` wraps the original validated Observation v1 intact and adds
explicit dataset/run, sensor ID/epoch, real/synthetic/unknown origin, and temporal
support. Simulated provenance must match the synthetic origin and run; measured and
self-reported provenance require real origin. Derived lineage remains in Observation
provenance; its real/synthetic ancestry is a caller declaration, not reconstructed
or authenticated by these schemas. Unknown ancestry cannot support a usable result.

The support interval `[start, end]` may be a point. Daily or aggregate measurements
must declare their actual support rather than pretending they are instantaneous.
Sensor ID and epoch are either both supplied or both absent. Exact source matching
requires known sensor and origin. Unknown compatibility is explicitly `unavailable`,
which requires an `unsupported` result. This version supports exact matching only;
no cross-sensor calibration or migration compatibility is inferred.

Included, excluded and conflicting records preserve complete observations; exclusions
and conflicts require nonempty unique reason codes. IDs are nonempty and unique
across partitions; no record can be both included and excluded. Additional lineage
IDs remain caller-declared references, not evidence of authenticity. Same-source,
same-context, simultaneous readings with different measurements cannot be included
as mutually consistent evidence. Excluded/conflicting records may preserve out-of-scope
or late data, but cannot contribute statistics or satisfy ordinary included evidence.
Contracts cannot prove that the producer supplied every source observation.

All timestamps require timezone-aware datetime or ISO text, normalize to UTC, and
reject numeric epochs and unresolved folded local times. Event time, ingestion time,
reference time, anchor time and assessment/decision time remain distinct. In
prospective mode every included record requires `ingested_at <= assessed_at` and
support ending no later than assessment; unknown or late availability is rejected
from inclusion. It must instead be excluded with a reason and the appropriate
abstaining status. Retrospective mode permits absent/late ingestion metadata and
must never be presented as an online replay. Observation v1's own ingestion/event
ordering constraints remain unchanged.

## Baseline declarations

`BaselinePolicy` requires every research parameter explicitly:

| Parameter | Meaning |
| --- | --- |
| source scope | Exact dataset, run, mission, subject, source, sensor and epoch |
| metric/unit | Registry-supported numeric astronaut metric and canonical unit |
| reference interval | Positive-duration event-time window `(start, end]` |
| bin duration | Positive seconds, at most the reference duration |
| minimum occupied bins | Positive count within available bin capacity |
| minimum observed span | Positive seconds within the reference interval |
| minimum occupancy fraction | Explicit fraction in `(0,1]` |
| maximum gap | Positive maximum between consecutive included event times |
| maximum reference age | Positive seconds from reference end to assessment |
| compatibility / availability | Explicit source policy and replay mode |

`ReferenceSummary` supplies total/occupied bins, sample count, bin membership,
occupancy fraction, observed span and largest consecutive gap. Bin index `i` denotes
`(start+i*duration, min(end,start+(i+1)*duration)]`; the final bin can be shorter.
Unoccupied bins are omitted, not filled with zero readings. Counts and memberships
must reconcile exactly with included IDs, boundaries and declared capacity.
Coverage is **occupied bins / total bins**, not a probability or a sample density.
Span/gap declarations must match included timestamps; zero or one included reading
has zero spread. Boundary-to-first/last silence is represented by occupancy/span
and freshness; `maximum_gap_seconds` measures consecutive readings only.

A `ready` profile requires valid-only compatible observations, sufficient declared
coverage/span, freshness, median and strictly positive raw MAD, with no abstention.
`flat_reference` requires the same coverage/compatibility checks, raw MAD exactly
zero, and abstention reasons. It can retain its median, but cannot support a scaled
score. `insufficient_reference` and `unsupported` require reasons and null median/MAD.
A producer may conservatively abstain even where structural coverage checks pass.
No epsilon, scaling constant, imputation, clinical norm or personal-health claim is
introduced. Validators do not recompute bin medians or MAD and cannot certify a
producer's statistical method; its version and future algorithm tests must do that.

## Anomaly declarations

`AnomalyPolicy` fixes the research definition
`absolute_deviation_over_raw_mad`, with canonical metric/unit, explicit governance
source, nullable calibration metadata and nullable approved research threshold.
The conceptual declared relationship is `abs(value - reference median) / raw MAD`;
it is dimensionless, **not a z-score, calibrated probability, severity or disease risk**.
Signed/absolute deviation and direction must agree with the supplied original value
and median; score declarations must agree with positive raw MAD.

`AnomalyFinding` requires original source value, assessment time, explicit score
status, threshold status, evidence/profile lineage, quality limitations, explanation,
method version and abstention reasons. Original missing/unavailable values stay
null; they are not converted to zero. The target follows the reference interval,
is not an included reference observation, and matches the profile's source identity.
A mismatched sensor, stale reference, unsupported unit or unavailable prospective
target requires `unsupported`; non-valid targets cannot be scored.

Only `scored` accepts a non-null raw-MAD score. All other statuses require a null
score and reasons. `flat_reference` may preserve raw deviations with a null score;
other unusable states cannot publish deviations. There are no probability,
confidence, diagnosis, severity or treatment fields. Explanation text is supplied by
a future deterministic producer; these schemas require it to be nonblank but cannot
prove its determinism or scientific truth.

Without an approved research threshold, `threshold_status` must be `unassessed`,
even when a score exists. Approval requires a positive threshold, explicit `>` or
`>=` comparison, approval reference/time and matching versioned calibration artifact
with source. A decision requires approval no later than assessment and must agree
with that explicit rule. Neither schema validation nor an approval-reference string
constitutes institutional approval, artifact authentication or clinical validation.
No numeric threshold defaults are supplied; all test thresholds are synthetic.

## Temporal declarations

`FusionPolicy` supplies a concrete positive event window, per-source identity,
metric/canonical unit and maximum age, maximum cross-source separation, exact context
matching, association requirement, eligible quality, missing/conflict treatment and
availability mode. Missing and conflict treatment is abstention in this version.
Only explicit valid/suspect quality eligibility is supported; no weights or implied
probabilities exist. Categorical/boolean metrics use unit `1`; numeric units remain
those of Observation v1. Pa and ppm are distinct metrics and never converted.

Groups anchor at the policy window end. Every included event and its entire support
must fit `(start, anchor]`; source age and separation limits are inclusive. This
prevents daily support being silently squeezed into minute windows. Age checks use
event timestamps; support is checked separately. Mission/subject/spacecraft/compartment
must match where present in the original scope. A mission-scoped observation does
not acquire compartment specificity by appearing in a group.

Combining subject and environmental scopes additionally requires an explicit
subject/spacecraft/compartment association, supporting IDs/source reference and an
interval covering all included temporal support. No location is inferred from
chronology. Mixed real/synthetic origins are prohibited in the included partition,
regardless of matching dates. Unpaired NASA/synthetic records can be retained as
excluded with `unsupported` status; their proximity is never association evidence.

| Group status | Contract requirement |
| --- | --- |
| aligned | Nonempty compatible included evidence, all source requirements covered, no conflicts or limitation reasons |
| no_data | No included or conflicting evidence; all source requirements missing; reasons required |
| insufficient_evidence | Some compatible included evidence, missing requirements, no conflicts; reasons required |
| conflicting_evidence | Explicit conflicting partition and reasons; no claim of alignment |
| unsupported | Explicit reasons; incompatible records stay outside included partition |

Missing requirements are IDs of policy sources absent from included/conflicting
partitions; ordinary exclusions do not satisfy a requirement. Conflicting records
preserve that evidence was present without representing it as aligned. Unavailable
source compatibility requires `unsupported`, which may also preserve conflicts.
These declarations do not establish causal direction, independent evidence, sensor
calibration, health effects or clinical readiness.

## Audit limitations carried forward

The prior Phase 4 audit found no real astronaut physiology, no longitudinal personal
baseline data, no anomaly calibration artifacts and no approved clinical thresholds.
Synthetic short episodes reuse a fictional crew identity across distinct missions;
they must not be pooled into a personal history. NASA RR-1 environmental records
have no validated pairing to that crew. CO2 concentration is ppm, separate from
synthetic partial pressure in Pa. Radiation rates have date-level timing limitations;
accumulated dose has unresolved source units and remains unavailable in the existing
adapter. Nothing in these contracts repairs or overrides those limitations.

## Future integration boundaries

- **M4.3:** separately authorized baseline estimator; validate its inputs, apply an
  explicit policy, report included/excluded lineage and coverage, compute method-
  versioned bin statistics, and emit these profiles. No such estimator exists here.
- **M4.4:** separately authorized anomaly producer; consume validated profiles and
  observations, emit deterministic research findings, and retain abstention. No
  scorer or calibration artifact is supplied here.
- **M4.5:** separately authorized temporal selector/group producer; enforce explicit
  availability, context and association policies and emit evidence groups. No join,
  probabilistic fusion, causal model or knowledge graph is supplied here.

Advanced outputs remain separate research sidecars. Future integration needs an
explicit application boundary and review; do not synthesize pseudo-observations or
change M2's established result. Observation v1, Investigation v1, M2 behavior, API,
frontend, datasets, generators, training and independent safety policies remain
unchanged. Passing software checks does not establish medical suitability.
