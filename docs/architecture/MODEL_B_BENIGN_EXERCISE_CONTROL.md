# Model B research-only benign exercise control

This module adds an in-memory `benign_exercise_control` scenario under
`simulator/research/`. It does not change `simulator/mission_generator.py`,
the four existing scenarios, or any existing dataset/export command.

## Scenario and target semantics

`generate_model_b_research_mission()` first calls the existing
`generate_mission()` unchanged. It then generates separate control episodes
with a deterministic SHA-256-derived random seed domain-separated by the
control scenario name and generator version. Episode IDs are checked against
the existing mission before combination.

Labels are stored in a separate in-memory mapping keyed by sample ID:

| Scenario | `expected_anomaly_proxy` |
| --- | ---: |
| `baseline` | false |
| `benign_exercise_control` | false |
| `elevated_co2` | true |
| `recent_exercise` | true |
| `sleep_deprivation` | true |

These are synthetic evaluation proxies, not clinical ground truth. No new
label or scenario name is placed in the predictor features.

## Measurement assumptions

The control uses the established six Model B observation metrics and their
existing units, domains, scope contracts, timestamps, dropout policy, and
five-minute feature builder. It marks `exercise_active` during the existing
configured exercise interval, uses the baseline generator’s CO₂, sleep,
fatigue, and communication-delay assumptions, and applies an exercise-related
heart-rate response with the same configured recovery curve.

To distinguish the control measurement pattern from the existing
`recent_exercise` proxy without adding a scenario-name feature, its heart-rate
response amplitude is multiplied by `response_fraction`, default `0.5` and
configurable strictly between zero and one. This lower-response contrast is a
toy generator assumption chosen for a synthetic control; it is not sourced
from clinical evidence, a normal range, or an alert threshold. The resulting
feature differences are observable only through the existing heart-rate and
exercise features.

Scenario and expected-label metadata remain outside the feature builder’s
returned `values`. The research extension returns data in memory only; it does
not write datasets or artifacts. Use a later, separately approved exporter
and split manifest for any train/validation/test generation.

## Determinism and limits

The existing mission retains the configured `SimulationConfig.seed`. The
control uses a stable derived seed and records that seed in its simulation
provenance. Same inputs produce the same observations, anchors, and labels;
different run seeds are expected to produce disjoint episode IDs and must be
checked across future split manifests.

This control makes the synthetic label distinction explicit and gives the
evaluation harness a benign exercise group for measuring exercise-associated
alerts. It does not establish that any generated response is medically normal
or that a detector can distinguish real exercise from a health hazard.
