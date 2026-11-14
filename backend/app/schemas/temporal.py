"""AI-H1 research contracts, independent of model runtimes and transport."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from app.schemas.baseline import (
    Count,
    ExcludedEvidence,
    Finite,
    Ids,
    Nonnegative,
    Positive,
    ResearchContract,
    ResearchEvidence,
    ResearchTime,
    Text,
    TimeInterval,
    unique_ids,
    validate_numeric_metric,
)
from app.schemas.environmental_anomaly_context import EnvironmentalAnomalyContext
from app.schemas.fusion import SourceRequirement
from app.schemas.observation import METRIC_REGISTRY, Contract, NumericMeasurement, Scope

Pattern = Literal[
    "persistent_anomaly",
    "isolated_spike",
    "recovery",
    "worsening",
    "improving",
    "no_pattern",
    "abstained",
]


class TemporalPolicy(ResearchContract):
    """Explicit statistical conventions, never medical reference ranges.

    Window is (start, end]; prospective availability is mandatory. Higher/lower
    worsening describes the caller's research direction, not health or safety.
    """

    policy_id: Text
    policy_version: Literal["1.0.0"]
    scope: Scope
    source: SourceRequirement
    event_window: TimeInterval
    reference_lower: Finite
    reference_upper: Finite
    trend_direction: Literal["higher_is_worsening", "lower_is_worsening"]
    minimum_slope_per_second: Positive
    minimum_observations: Annotated[int, Field(strict=True, ge=3)]
    minimum_run: Annotated[int, Field(strict=True, ge=2)]
    maximum_gap_seconds: Positive
    convention_reference: Text

    @model_validator(mode="after")
    def consistent(self) -> Self:
        validate_numeric_metric(self.source.metric, self.source.unit)
        if self.scope.kind not in METRIC_REGISTRY[self.source.metric].scopes:
            raise ValueError("metric is incompatible with requested scope")
        if self.event_window.start >= self.event_window.end:
            raise ValueError("positive duration window required")
        if self.reference_lower > self.reference_upper:
            raise ValueError("ordered statistical reference bounds required")
        if self.minimum_run > self.minimum_observations:
            raise ValueError("minimum run cannot exceed minimum observations")
        return self


class ModelContextEvidence(Contract):
    """Original sidecar retained intact; multivariate flags are never metric flags."""

    context: EnvironmentalAnomalyContext
    used: bool
    reason_codes: Ids

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.used == bool(self.reason_codes):
            raise ValueError("unused model contexts require exclusion reasons")
        return self


class TemporalSummary(ResearchContract):
    method_version: Literal["temporal-evidence-1.0.0"]
    policy: TemporalPolicy
    assessed_at: ResearchTime
    pattern: Pattern
    observation_ids: Ids
    valid_observation_count: Count
    event_span: TimeInterval | None
    observed_span_seconds: Nonnegative
    slope_per_second: Finite | None
    supporting_evidence: tuple[ResearchEvidence, ...]
    excluded_evidence: tuple[ExcludedEvidence, ...]
    model_contexts: tuple[ModelContextEvidence, ...]
    missing_or_unavailable: Ids
    quality_limitations: Ids
    abstention_reasons: Ids

    @model_validator(mode="after")
    def consistent(self) -> Self:
        evidence = self.supporting_evidence
        if self.assessed_at < self.policy.event_window.end:
            raise ValueError("assessment must follow the event window")
        if self.observation_ids != tuple(
            e.observation.observation_id for e in evidence
        ):
            raise ValueError(
                "ordered observation lineage must match supporting evidence"
            )
        if self.valid_observation_count != len(evidence):
            raise ValueError("valid count must match supporting evidence")
        unique_ids(
            self.observation_ids
            + tuple(
                e.evidence.observation.observation_id for e in self.excluded_evidence
            )
        )
        times = [e.observation.timestamp for e in evidence]
        if times != sorted(set(times)):
            raise ValueError("support must have distinct ordered event times")
        expected = TimeInterval(start=times[0], end=times[-1]) if times else None
        if self.event_span != expected:
            raise ValueError("span must match supporting event times")
        seconds = (times[-1] - times[0]).total_seconds() if times else 0.0
        if self.observed_span_seconds != seconds:
            raise ValueError("duration must match supporting evidence")
        if (self.pattern == "abstained") != bool(self.abstention_reasons):
            raise ValueError("abstention pattern and reasons must agree")
        p = self.policy
        if self.pattern != "abstained":
            if len(evidence) < p.minimum_observations:
                raise ValueError("usable summary requires minimum evidence")
            if (
                self.assessed_at - times[-1]
            ).total_seconds() > p.source.maximum_age_seconds:
                raise ValueError("usable summary requires fresh observations")
            edges = [p.event_window.start, *times, p.event_window.end]
            if any(
                (b - a).total_seconds() > p.maximum_gap_seconds
                for a, b in zip(edges, edges[1:], strict=False)
            ):
                raise ValueError("usable summary cannot bridge excessive gaps")
        elif self.slope_per_second is not None:
            raise ValueError("abstained summary cannot publish a trend statistic")
        for item in evidence:
            obs = item.observation
            if (
                not p.source.matches(item)
                or obs.scope != p.scope
                or obs.quality.status != "valid"
                or not isinstance(obs.measurement, NumericMeasurement)
                or obs.measurement.unit != p.source.unit
                or not item.available_at(self.assessed_at, "prospective")
                or not p.event_window.start
                < item.temporal_support.start
                <= item.temporal_support.end
                <= p.event_window.end
            ):
                raise ValueError("support must be compatible, valid and available")
        return self
