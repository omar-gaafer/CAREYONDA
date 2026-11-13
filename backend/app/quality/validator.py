"""Pure quality evaluation and a privacy-preserving structural validation boundary."""

from dataclasses import dataclass

from pydantic import ValidationError

from app.schemas.observation import (
    METRIC_REGISTRY,
    NumericMeasurement,
    Observation,
    QualityStatus,
)


@dataclass(frozen=True)
class ValidationIssue:
    """Safe codes/locations only: no raw inputs, exception context, or measurements."""

    location: tuple[str | int, ...]
    code: str


@dataclass(frozen=True)
class QualityAssessment:
    status: QualityStatus
    reason_codes: tuple[str, ...]


class ObservationValidationError(ValueError):
    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__("Observation contract validation failed")


def validate_observation(payload: object) -> Observation:
    """Validate untrusted input without exposing its values in error details."""
    try:
        return Observation.model_validate(payload)
    except ValidationError as error:
        issues = tuple(
            ValidationIssue(tuple(item["loc"]), item["type"])
            for item in error.errors(
                include_input=False, include_context=False, include_url=False
            )
        )
        raise ObservationValidationError(issues) from None


def evaluate_quality(observation: Observation) -> QualityAssessment:
    """Report physical-domain violations without mutating or discarding evidence.

    This is not clinical evaluation. Invalid source quality is never upgraded.
    Structurally malformed data must use the validation boundary first.
    """
    reasons = observation.quality.reason_codes
    if isinstance(observation.measurement, NumericMeasurement):
        definition = METRIC_REGISTRY[observation.metric]
        value = observation.measurement.value
        below = definition.minimum is not None and value < definition.minimum
        above = definition.maximum is not None and value > definition.maximum
        if below or above:
            return QualityAssessment(
                "invalid", tuple(dict.fromkeys((*reasons, "physical_domain_violation")))
            )
    return QualityAssessment(observation.quality.status, reasons)
