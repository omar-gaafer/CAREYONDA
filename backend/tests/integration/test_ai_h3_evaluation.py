"""Harness integrity and frozen-contract regression tests, not medical validation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from examples.ai_h3_evaluation import (
    SPEC_PATH,
    Challenge,
    evaluation_report,
    load_specification,
    run_challenge,
    score,
)


@pytest.mark.parametrize("challenge", load_specification().cases, ids=lambda c: c.id)
def test_frozen_challenge(challenge: Challenge) -> None:
    trial = run_challenge(challenge)
    actual = score(challenge, trial)
    if challenge.inputs.duplicate:
        assert trial.boundary_error == "duplicate observation IDs"
        assert trial.m2 is None
        assert trial.temporal is None
        assert trial.hybrid is None
        assert actual["eligible"] is False
        return
    assert actual["association_correct"] is True
    assert actual["temporal_correct"] is True
    assert actual["abstention_correct"] is True
    assert actual["unsupported_directional_assertions"] == 0
    assert actual["traced_references"] == actual["directional_references"]
    assert actual["m2_unchanged"] is True


def test_configuration_capabilities_and_invariance() -> None:
    challenge = load_specification().cases[0]
    a = run_challenge(challenge, configuration="A")
    b = run_challenge(challenge, configuration="B")
    c = run_challenge(challenge, configuration="C")
    assert a.temporal is None
    assert a.hybrid is None
    assert b.hybrid is None
    assert a.m2 == b.m2 == c.m2
    assert b.temporal == c.temporal
    assert c.hybrid is not None
    assert c.hybrid.original_investigation == a.m2


def test_expectation_edits_rejected_before_evaluation(tmp_path: Path) -> None:
    altered = tmp_path / "altered-spec.json"
    altered.write_bytes(SPEC_PATH.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="frozen SHA-256"):
        load_specification(altered)


def test_scorer_detects_false_direction_and_provenance_loss() -> None:
    challenge = load_specification().cases[0]
    trial = run_challenge(challenge)
    assert trial.hybrid is not None
    # Deliberately bypass validation to fault-inject a damaged prediction into the
    # metric layer. Expectations remain untouched and are never learned from output.
    corrupted = trial.hybrid.model_copy(
        update={
            "supporting_evidence_ids": (
                *trial.hybrid.supporting_evidence_ids,
                "unobserved",
            ),
            "evidence_snapshots": (),
            "abstention_reasons": ("spurious_abstention",),
        }
    )
    result = score(challenge, replace(trial, hybrid=corrupted))
    assert result["association_correct"] is False
    assert result["unsupported_directional_assertions"] == 1
    assert result["traced_references"] == 0
    assert result["abstention_correct"] is False


def test_scorer_detects_wrong_contradiction_direction() -> None:
    challenge = next(c for c in load_specification().cases if c.id == "contradiction")
    trial = run_challenge(challenge)
    assert trial.hybrid is not None
    corrupted = trial.hybrid.model_copy(update={"contradicting_evidence_ids": ()})
    assert (
        score(challenge, replace(trial, hybrid=corrupted))["contradiction_correct"]
        is False
    )


def test_report_reproduction_accounting_and_na() -> None:
    actual = evaluation_report()
    archived = json.loads((SPEC_PATH.parent / "AI_H3_RESULTS.json").read_text())
    # JSON round trip normalizes tuples, without ignoring any result fields.
    assert json.loads(json.dumps(actual)) == archived
    assert actual["challenge_count"] == 13
    assert actual["eligible_count"] == 12
    assert actual["boundary_rejections"] == 1
    metrics = actual["metrics"]
    assert isinstance(metrics, dict)
    for name in ("A", "B", "C"):
        assert metrics[name]["deterministic_reproducibility"] == {
            "correct": 13,
            "total": 13,
        }
    for name in ("A", "B"):
        assert metrics[name]["evidence_association_correctness"]["value"] is None
    assert metrics["A"]["temporal_pattern_recognition"]["value"] is None
    assert metrics["C"]["evidence_association_correctness"] == {
        "correct": 12,
        "total": 12,
    }
    assert actual["development_cases"] == {
        "count": 12,
        "source": "examples.hybrid_research_cases",
        "included_in_challenge_metrics": False,
    }
