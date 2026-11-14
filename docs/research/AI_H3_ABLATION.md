# AI-H3 research evaluation and ablation

## Integrity and reproduction

Engine baseline: `7b56152c5bad72dd9446f17c301dcc466b16bd6a`. See [protocol](AI_H3_PROTOCOL.md), [frozen specification](AI_H3_CHALLENGE_SPEC.json) and [machine-readable results](AI_H3_RESULTS.json). Run from `backend`: `PYTHONPATH=. python -m examples.ai_h3_evaluation`. The runner verifies the specification digest before invoking any engine and emits sorted, deterministic JSON; no runtime clock, random sampling, downloads or fitted artifacts.

The historical AI-H2 **12/12 is development-test performance**, not held-out validation. Those cases were used to implement/debug H2. This challenge uses 13 separately specified contract cases after the engine freeze: 12 eligible shared-input cases and one duplicate-input boundary rejection. Expectations were written and hashed before the first evaluation and were not changed after observing outputs. The first completed evaluation matched all eligible expectations. Subsequent harness changes added explicitly separate A/B/C execution paths and corrected a static tuple annotation; no engine, expectation or fixture values changed. Generic artificial Model A context construction is reused from development fixtures; no independence claim applies to that helper.

## Capability ablation

A runs M2 only. B independently runs M2 and adds H1's descriptive temporal summary. C independently runs M2, H1 and H2. Adding a sidecar neither reranks hypotheses nor introduces new M2 findings. Common inputs include current/reference observations and anchors; sidecars additionally receive their explicit source, scope, temporal and association policies. Reference scope mismatches are intentional: M2's retrospective reference comparison accepts separate reference contexts, whereas H2 requires exact scope identity.

| Metric (protocol definition) | A: M2 | B: M2 + H1 | C: M2 + H1 + H2 |
|---|---:|---:|---:|
| Prospective evidence association, exact status + ID sets | N/A | N/A | 12/12 |
| Hybrid contradiction ID handling | N/A | N/A | 1/1 |
| Hybrid abstention decision + reason consistency | N/A | N/A | 12/12 |
| Unsupported hybrid directional ID assertions | N/A | N/A | 0 |
| Embedded directional current/reference ID resolution | N/A | N/A | 56/56 |
| Temporal label agreement | N/A | 12/12 | 12/12 |
| Repeat and reversed-input complete-output agreement | 13/13 | 13/13 | 13/13 |

M2 investigations remained identical across all three configurations on 12/12 eligible cases. B/C temporal outputs also matched exactly. Duplicate observations are rejected by M2 before either sidecar runs; all configurations reproduce that boundary result. They are excluded from semantic metric denominators rather than counted as semantic successes. Hybrid abstention agreement includes both abstaining and non-abstaining cases; retained partial supporting evidence is not itself a failure to abstain.

N/A means an absent research contract, not poor performance. M2 does emit native retrospective supporting/contradictory findings and selection uncertainty; these are preserved in the JSON. This report deliberately does not equate M2 selection abstention with H2 association abstention. The contradiction metric specifically concerns H2's prospective association contract, not M2's native contradiction detection. This is a capability/contract ablation, **not a claim that C has superior predictive accuracy**. Provenance completeness means ID-to-snapshot resolution, not authentic provenance, feature attribution or cross-model readiness.

## Case outcomes

M2 column reports compatibility of the existing sleep_deprivation toy hypothesis, not a diagnosis or selected clinical cause.

| Challenge | M2 native target compatibility | H1 pattern | H2 association | Oracle |
|---|---|---|---|---|
| persistent | supported | persistent_anomaly | supported_by_available_evidence | matched |
| isolated | supported | isolated_spike | insufficient_evidence | matched |
| missing | supported | abstained | insufficient_evidence | matched |
| contradiction | mixed | persistent_anomaly | mixed_evidence | matched |
| wrong-mission | supported | persistent_anomaly | incompatible_evidence | matched |
| wrong-subject | supported | persistent_anomaly | incompatible_evidence | matched |
| duplicate | input rejected | N/A | N/A | expected boundary rejection |
| future-unavailable | supported | persistent_anomaly | insufficient_evidence | matched |
| model-abstention | supported | persistent_anomaly | insufficient_evidence | matched |
| recovery | supported | recovery | supported_by_available_evidence | matched |
| conflicting-provenance | supported | persistent_anomaly | incompatible_evidence | matched |
| nasa-replay-scope | supported | persistent_anomaly | insufficient_evidence | matched |
| stale | supported | abstained | insufficient_evidence | matched |

The isolated sequence still has an empirical mean below M2's reference minimum, while H1 identifies one spike; H2 correctly withholds the persistent-sequence association. Recovery uses an explicitly different declared temporal rule accepting return to the arbitrary band. It is not an inferred improvement in health. Future-unavailable reference evidence remains usable to retrospective M2 but cannot establish a prospective H2 association. Wrong mission/subject and conflicting provenance are quarantined rather than silently pooled. Model abstention and NASA replay cases require a compatible model context, so their otherwise valid raw supporting IDs coexist with overall insufficient evidence.

## Verification and limits

Automated tests check all frozen challenges, configuration capabilities/invariance, digest tamper rejection, fault-injected false-direction/provenance/contradiction detection, and full JSON reproduction. Existing M2, H1, H2 and Model A tests remain regressions, separate from challenge performance. Final verification: **566 passed, 2 skipped** in the complete pytest suite (548 pre-existing passing regressions plus 18 new evaluation tests). The two skips require explicit trusted local Model A artifacts or NASA RR-1 CSV files, neither loaded for this milestone. After test-assertion typing cleanup, the 18 focused tests passed again. Ruff passed over app/tests/examples; formatting checked 85 files. Strict mypy passed the configured 84-file scope and the two new Python files explicitly. Git staged whitespace checks passed before commit.

Commands from `backend` (using already-provisioned dependencies):

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -rs
python -m ruff check app tests examples
python -m ruff format --check app tests examples
python -m mypy --explicit-package-bases --python-executable /tmp/careyonda-model-a-python312/bin/python
python -m mypy --strict --explicit-package-bases --python-executable /tmp/careyonda-model-a-python312/bin/python examples/ai_h3_evaluation.py tests/integration/test_ai_h3_evaluation.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m examples.ai_h3_evaluation > /tmp/ai-h3-results.json
cmp /tmp/ai-h3-results.json ../docs/research/AI_H3_RESULTS.json
git diff --cached --check
```

Actual test/evaluation interpreter: `/tmp/careyonda-model-a-python312/bin/python` (3.12.10). Ruff/mypy interpreter: `/home/darknight90/CAREYONDA/backend/.venv/bin/python`. No packages installed. Run pytest with the project’s normal local execution permissions; the sandboxed TestClient transport had hung during baseline verification, while the full suite completed with authorized local execution. This is an environment limitation, not a skipped test category.

This small, authored synthetic set has one contradiction case, no fitted-model execution, no Model B adapter, no NASA values and no independently authenticated source availability. It is not statistically representative or blinded; policy selection is explicit and case-specific for recovery. The model-abstention fixture also carries a nonmatching environmental scope; it tests rejection of an unavailable context, not isolated attribution to the abstention gate. No compatible available-model positive control is established for these astronaut cases. Results do not establish clinical accuracy, calibrated confidence, hazard severity, causal attribution or operational readiness. Software tests and provenance hashes do not change those limits.

## Final sprint handoff

Hand off the frozen specification, runner, result JSON and [Model B compatibility review](AI_H3_MODEL_B_COMPATIBILITY.md) together. Review and publish the Model B contract, then separately authorize a typed research-only adapter with genuine availability and evidence lineage before cross-model evaluation. Commission externally authored held-out cases and broader contradiction/negative controls before making generalization claims. Keep historical NASA replay isolated. No further algorithms, integration, merge or push are part of this milestone.
