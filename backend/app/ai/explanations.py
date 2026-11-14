"""Deterministic explanations from structured evidence, without medical actions."""

from collections.abc import Sequence

from app.schemas.evidence import EvidenceFinding
from app.schemas.investigation import Compatibility, HypothesisId


def explain_hypothesis(
    hypothesis: HypothesisId,
    compatibility: Compatibility,
    supporting: Sequence[EvidenceFinding],
    contradictory: Sequence[EvidenceFinding],
    missing: Sequence[EvidenceFinding],
) -> str:
    parts = [f"{hypothesis}: {compatibility} under reference-rules-1.0.0."]
    for label, findings in (
        ("Supporting", supporting),
        ("Contradictory", contradictory),
        ("Missing or unusable", missing),
    ):
        if findings:
            parts.append(
                f"{label}: " + "; ".join(f.explanation for f in findings) + "."
            )
    parts.append(
        "Pattern compatibility does not establish causation, diagnosis, or safety."
    )
    return " ".join(parts)
