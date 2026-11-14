"""Model C — deterministic sleep/fatigue research monitor contracts (v1.1.0).

Per-subject comparison of supported behavioural indicators against that subject's
own declared reference period. Research decision support only: no diagnosis,
condition label, treatment, operational action, risk or severity score.

Numeric indicators reuse the M4.2 ``BaselineProfile`` and ``AnomalyFinding``
contracts unchanged. Categorical self-reports, which M4.2 numeric contracts do not
support, are summarised descriptively as category counts without any score.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal, Self

from pydantic import Field, model_validator

from app.schemas.anomaly import AnomalyFinding, AnomalyPolicy
from app.schemas.baseline import (
    AvailabilityMode,
    BaselineProfile,
    Count,
    ExcludedEvidence,
    Fraction,
    Ids,
    Nonnegative,
    Positive,
    PositiveCount,
    ResearchContract,
    ResearchEvidence,
    ResearchTime,
    Text,
    TimeInterval,
)
from app.schemas.observation import METRIC_REGISTRY, Contract, Identifier

MODEL_C_ID: Final = "careyonda-model-c-isolation-confinement"
MODEL_C_VERSION: Final = "1.1.0"

NumericIndicator = Literal["sleep_duration"]
CategoricalIndicator = Literal["fatigue_self_report"]
Indicator = Literal["sleep_duration", "fatigue_self_report"]
SUPPORTED_INDICATORS: Final[tuple[str, ...]] = ("sleep_duration", "fatigue_self_report")

# How the registry characterises each metric. No contract declares whether
# ``sleep_duration`` is measured or self-reported; each record's provenance decides.
RegistryReportingMode = Literal["unspecified_by_contract", "self_report"]
REGISTRY_REPORTING_MODE: Final[dict[str, RegistryReportingMode]] = {
    "sleep_duration": "unspecified_by_contract",
    "fatigue_self_report": "self_report",
}
ProvenanceNature = Literal["direct_measurement", "self_report", "derived", "simulated"]

LIMITATIONS: Final[tuple[str, ...]] = (
    "Research only: within-person statistical deviation is not a diagnosis, "
    "condition label, probability, severity or risk.",
    "Comparisons use only this subject's own declared reference period; no "
    "population norm or universal normal range is applied.",
    "All statistical parameters are configurable research defaults, not "
    "validated clinical, NASA-approved or operational limits.",
    "Indicators are reported separately and never combined into a composite score.",
    "Change relative to a reference period does not establish a cause; isolation, "
    "confinement or any other factor is not inferred as the reason.",
    "Missing, invalid or unavailable records are preserved as abstentions or "
    "exclusions, never treated as normal values.",
    "No recommendation, treatment or operational action is produced; outputs "
    "require qualified human review.",
)


InstrumentKind = Literal["sensor", "self_report_form"]
# Provenance origins each instrument kind may carry. A self-report form never
# produces ``measured`` data; a sensor never produces ``self_reported`` data.
INSTRUMENT_ORIGINS: Final[dict[str, frozenset[str]]] = {
    "sensor": frozenset({"measured", "derived", "simulated"}),
    "self_report_form": frozenset({"self_reported", "simulated"}),
}


class IndicatorSource(Contract):
    """Caller-declared source identity for one indicator (exact matching only).

    ``instrument_kind`` (added in 1.1.0) states what produced the records. For a
    ``sensor`` the ``sensor_id``/``sensor_epoch`` pair is the device identity. For
    a ``self_report_form`` that pair is the *form identifier and form version*:
    the actual reporting instrument, never a physical device. It occupies the
    M4.2 sensor slot only so that exact-identity matching can be applied to the
    same form version; outputs always repeat ``instrument_kind``.
    """

    indicator: Indicator
    instrument_kind: InstrumentKind
    source_id: Identifier
    sensor_id: Identifier | None
    sensor_epoch: Identifier | None

    @model_validator(mode="after")
    def sensor_pair(self) -> Self:
        if (self.sensor_id is None) != (self.sensor_epoch is None):
            raise ValueError("sensor identity and epoch must be supplied together")
        if self.indicator == "fatigue_self_report" and (
            self.instrument_kind != "self_report_form"
        ):
            raise ValueError("fatigue_self_report requires a self_report_form")
        if self.instrument_kind == "self_report_form" and self.sensor_id is None:
            raise ValueError("a self-report form requires its form id and version")
        return self


class ModelCParameters(Contract):
    """Explicit research parameters; none is a validated or approved limit."""

    parameter_status: Literal["unvalidated_research_default", "caller_supplied"]
    bin_duration_seconds: Positive
    minimum_occupied_bins: PositiveCount
    minimum_observed_span_seconds: Positive
    minimum_occupancy_fraction: Annotated[Fraction, Field(gt=0)]
    maximum_gap_seconds: Positive
    maximum_reference_age_seconds: Positive
    minimum_reference_reports: PositiveCount
    availability_mode: AvailabilityMode


class ModelCRequest(ResearchContract):
    """One subject, one dataset/run, explicit reference and assessment periods."""

    subject_id: Identifier
    mission_id: Identifier
    dataset_id: Identifier
    run_id: Identifier
    data_origin: Literal["synthetic", "real"]
    assessed_at: ResearchTime
    reference_interval: TimeInterval
    assessment_interval: TimeInterval
    sources: Annotated[tuple[IndicatorSource, ...], Field(min_length=1)]
    parameters: ModelCParameters
    anomaly_policy: AnomalyPolicy | None = None
    evidence: tuple[ResearchEvidence, ...]

    @model_validator(mode="after")
    def consistent_request(self) -> Self:
        ref, window = self.reference_interval, self.assessment_interval
        if not (ref.start < ref.end <= window.start < window.end <= self.assessed_at):
            raise ValueError(
                "require reference start < reference end <= assessment start "
                "< assessment end <= assessed_at"
            )
        indicators = [s.indicator for s in self.sources]
        if len(set(indicators)) != len(indicators):
            raise ValueError("each indicator may declare one source")
        policy = self.anomaly_policy
        if policy is not None and (
            "sleep_duration" not in indicators
            or (policy.metric, policy.unit) != ("sleep_duration", "h")
        ):
            raise ValueError("anomaly policy must target a declared sleep_duration")
        if (
            policy is not None
            and policy.threshold is not None
            and policy.threshold.approved_at > self.assessed_at
        ):
            raise ValueError("research threshold approval cannot follow assessment")
        ids = [e.observation.observation_id for e in self.evidence]
        if len(set(ids)) != len(ids):
            raise ValueError("evidence observation IDs must be unique")
        kinds = {s.indicator: s.instrument_kind for s in self.sources}
        for item in self.evidence:
            obs = item.observation
            if obs.metric not in indicators:
                raise ValueError("evidence metric has no declared Model C source")
            if obs.provenance.origin not in INSTRUMENT_ORIGINS[kinds[obs.metric]]:
                raise ValueError("evidence provenance contradicts the instrument kind")
            if (
                obs.scope.kind != "astronaut"
                or obs.scope.astronaut_id != self.subject_id
                or obs.scope.mission_id != self.mission_id
            ):
                raise ValueError("evidence belongs to another subject or mission")
            if (
                item.dataset_id != self.dataset_id
                or item.run_id != self.run_id
                or item.data_origin != self.data_origin
            ):
                raise ValueError("evidence dataset, run or data origin differs")
        return self


class FindingSummary(Contract):
    """Bookkeeping over one indicator's findings; not a probability or severity."""

    findings: Count
    scored: Count
    above_reference: Count
    below_reference: Count
    equal_to_reference: Count
    abstained: Count
    median_raw_mad_score: Nonnegative | None
    maximum_raw_mad_score: Nonnegative | None
    threshold_exceeded: Count

    @model_validator(mode="after")
    def consistent(self) -> Self:
        directions = self.above_reference + self.below_reference
        if self.scored + self.abstained != self.findings:
            raise ValueError("scored and abstained findings must sum to total")
        if directions + self.equal_to_reference != self.scored:
            raise ValueError("direction counts must sum to scored findings")
        if (self.scored == 0) != (self.median_raw_mad_score is None) or (
            self.scored == 0
        ) != (self.maximum_raw_mad_score is None):
            raise ValueError("score summaries exist only when findings were scored")
        if self.threshold_exceeded > self.scored:
            raise ValueError("threshold decisions require scored findings")
        return self


class NumericIndicatorAssessment(Contract):
    kind: Literal["numeric_personal_baseline"]
    indicator: NumericIndicator
    unit: Literal["h"]
    registry_reporting_mode: RegistryReportingMode
    instrument_kind: InstrumentKind
    evidence_provenance: tuple[ProvenanceNature, ...]
    status: Literal["assessed", "abstained"]
    baseline: BaselineProfile
    findings: tuple[AnomalyFinding, ...]
    summary: FindingSummary
    explanation: Text
    abstention_reasons: Ids

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.status == "assessed") == bool(self.abstention_reasons):
            raise ValueError("only assessed indicators may omit abstention reasons")
        if self.status == "assessed" and (
            self.baseline.status != "ready" or self.summary.scored == 0
        ):
            raise ValueError("assessed indicator requires ready baseline and a score")
        if self.summary.findings != len(self.findings) or self.summary.scored != sum(
            f.score_status == "scored" for f in self.findings
        ):
            raise ValueError("summary must reconcile with findings")
        if any(f.baseline != self.baseline for f in self.findings):
            raise ValueError("every finding must cite this indicator's baseline")
        return self


class CategoryCount(Contract):
    category: Identifier
    reference_count: Count
    assessment_count: Count


class CategoricalIndicatorAssessment(Contract):
    kind: Literal["categorical_report_distribution"]
    indicator: CategoricalIndicator
    registry_reporting_mode: RegistryReportingMode
    instrument_kind: InstrumentKind
    evidence_provenance: tuple[ProvenanceNature, ...]
    status: Literal["assessed", "abstained"]
    categories: tuple[CategoryCount, ...]
    reference_report_ids: Ids
    assessment_report_ids: Ids
    excluded: tuple[ExcludedEvidence, ...]
    explanation: Text
    abstention_reasons: Ids

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.status == "assessed") == bool(self.abstention_reasons):
            raise ValueError("only assessed indicators may omit abstention reasons")
        expected = METRIC_REGISTRY[self.indicator].categories
        if tuple(c.category for c in self.categories) != expected:
            raise ValueError("categories must follow the registry order exactly")
        if sum(c.reference_count for c in self.categories) != len(
            self.reference_report_ids
        ) or sum(c.assessment_count for c in self.categories) != len(
            self.assessment_report_ids
        ):
            raise ValueError("category counts must reconcile with report lineage")
        if set(self.reference_report_ids) & set(self.assessment_report_ids):
            raise ValueError("a report cannot belong to both periods")
        return self


IndicatorAssessment = Annotated[
    NumericIndicatorAssessment | CategoricalIndicatorAssessment,
    Field(discriminator="kind"),
]


class IsolationConfinementAssessment(ResearchContract):
    """Per-indicator results for one subject. Deliberately has no overall score."""

    model_id: Literal["careyonda-model-c-isolation-confinement"]
    model_version: Literal["1.1.0"]
    method_version: Identifier
    assessment_id: Identifier
    subject_id: Identifier
    mission_id: Identifier
    dataset_id: Identifier
    run_id: Identifier
    data_origin: Literal["synthetic", "real"]
    assessed_at: ResearchTime
    reference_interval: TimeInterval
    assessment_interval: TimeInterval
    parameters: ModelCParameters
    indicators: Annotated[tuple[IndicatorAssessment, ...], Field(min_length=1)]
    status: Literal["assessed", "partially_assessed", "abstained"]
    abstention_reasons: Ids
    unused_evidence_ids: Ids
    safety_status: Literal["not_evaluated"] = "not_evaluated"
    limitations: tuple[Text, ...] = LIMITATIONS

    @model_validator(mode="after")
    def consistent(self) -> Self:
        assessed = sum(i.status == "assessed" for i in self.indicators)
        expected = (
            "assessed"
            if assessed == len(self.indicators)
            else "abstained"
            if assessed == 0
            else "partially_assessed"
        )
        if self.status != expected:
            raise ValueError("overall status must reflect indicator statuses")
        if (self.status == "abstained") != bool(self.abstention_reasons):
            raise ValueError("abstention reasons accompany a fully abstained result")
        names = [i.indicator for i in self.indicators]
        if len(set(names)) != len(names):
            raise ValueError("each indicator is reported once")
        if not set(LIMITATIONS) <= set(self.limitations):
            raise ValueError("Model C research limitations must be retained")
        return self
