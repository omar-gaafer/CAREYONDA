"""Model B canonical reconciliation v2: synthetic, policy-neutral research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, StrictFloat, model_validator

from app.schemas.baseline import Ids, ResearchEvidence, ResearchTime, Text
from app.schemas.observation import (
    CompartmentScope,
    Contract,
    Identifier,
    SpacecraftScope,
)

FEATURE_ORDER = (
    "heart_rate_latest",
    "heart_rate_missing",
    "heart_rate_mean",
    "cabin_co2_partial_pressure_latest",
    "cabin_co2_partial_pressure_missing",
    "cabin_co2_partial_pressure_mean",
    "sleep_duration_latest",
    "sleep_duration_missing",
    "sleep_duration_mean",
    "fatigue_self_report_latest",
    "fatigue_self_report_missing",
    "communication_delay_latest",
    "communication_delay_missing",
    "communication_delay_mean",
    "exercise_active_latest",
    "exercise_active_missing",
)
FEATURE_UNITS = (
    "bpm",
    "1",
    "bpm",
    "Pa",
    "1",
    "Pa",
    "h",
    "1",
    "h",
    "1",
    "1",
    "s",
    "1",
    "s",
    "1",
    "1",
)
Finite = Annotated[StrictFloat, Field(allow_inf_nan=False)]
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
SCENARIOS = ("baseline", "elevated_co2", "recent_exercise", "sleep_deprivation")
Scenario = Literal["baseline", "elevated_co2", "recent_exercise", "sleep_deprivation"]
LIMITATIONS = (
    "Synthetic-scenario research only; not clinical performance or a diagnosis.",
    "Higher scores mean statistical atypicality, not probability, severity or causality.",
    "Exercise can be statistically atypical without illness or unsafe conditions.",
    "Features use retrospective event time, not verified online arrival availability.",
    "Deviation summaries are descriptive, not causal or model-faithful explanations.",
    "Safety not evaluated; no treatment or spacecraft action is authorized.",
)


class ModelBContext(Contract):
    sample_id: Identifier
    episode_id: Identifier
    mission_id: Identifier
    astronaut_id: Identifier
    spacecraft_id: Identifier
    compartment_id: Identifier
    timestamp: ResearchTime


class ModelBInput(Contract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    interpretation: Literal["synthetic_research_only"] = "synthetic_research_only"
    source_origin: Literal["simulated"] = "simulated"
    dataset_manifest_sha256: Digest
    dataset_id: Identifier
    run_id: Identifier
    context: ModelBContext
    assessed_at: ResearchTime
    availability_mode: Literal["retrospective", "prospective"]
    historical_source_availability: Literal["unknown"] = "unknown"
    acquired_at: ResearchTime | None
    acquisition_reference: Text | None
    feature_order: tuple[Identifier, ...]
    units: tuple[str, ...]
    values: tuple[Finite | None, ...]
    feature_evidence_ids: tuple[Ids, ...]
    window_observation_ids: Ids
    evidence: tuple[ResearchEvidence, ...]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.feature_order != FEATURE_ORDER or self.units != FEATURE_UNITS:
            raise ValueError("exact Model B feature order and canonical units required")
        if len(self.values) != 16 or len(self.feature_evidence_ids) != 16:
            raise ValueError("sixteen values and lineage lists required")
        if self.context.timestamp > self.assessed_at:
            raise ValueError("future event cannot be assessed")
        if (self.acquired_at is None) != (self.acquisition_reference is None):
            raise ValueError("acquisition time and reference must coexist")
        if (
            self.acquired_at is not None
            and not self.context.timestamp <= self.acquired_at <= self.assessed_at
        ):
            raise ValueError("future-unavailable acquisition")
        ids = tuple(e.observation.observation_id for e in self.evidence)
        if len(ids) != len(set(ids)) or set(ids) != set(self.window_observation_ids):
            raise ValueError(
                "window lineage must resolve uniquely to original evidence"
            )
        for e in self.evidence:
            obs = e.observation
            scope = obs.scope
            if (e.dataset_id, e.run_id, e.data_origin) != (
                self.dataset_id,
                self.run_id,
                "synthetic",
            ) or obs.provenance.origin != "simulated":
                raise ValueError(
                    "synthetic source identity required; no real-data fallback"
                )
            if scope.mission_id != self.context.mission_id:
                raise ValueError("mission mismatch")
            if (
                scope.kind == "astronaut"
                and scope.astronaut_id != self.context.astronaut_id
            ):
                raise ValueError("subject mismatch")
            if (
                isinstance(scope, (SpacecraftScope, CompartmentScope))
                and scope.spacecraft_id != self.context.spacecraft_id
            ):
                raise ValueError("spacecraft mismatch")
            if (
                scope.kind == "compartment"
                and scope.compartment_id != self.context.compartment_id
            ):
                raise ValueError("compartment mismatch")
            if e.temporal_support.end > self.context.timestamp:
                raise ValueError("support extends beyond feature event")
        lookup = dict(zip(FEATURE_ORDER, self.values, strict=True))
        for i, name in enumerate(FEATURE_ORDER):
            value, lineage = self.values[i], self.feature_evidence_ids[i]
            if not set(lineage) <= set(ids):
                raise ValueError("missing lineage")
            if value is not None and abs(value) > 3.4028234663852886e38:
                raise ValueError("value exceeds estimator representation")
            if name.endswith("_missing"):
                if value not in (0.0, 1.0):
                    raise ValueError("missing indicator must be binary")
                prefix = name.removesuffix("_missing")
                if (lookup[prefix + "_latest"] is None) != (value == 1.0):
                    raise ValueError("missingness contradicts latest value")
                if prefix + "_mean" in lookup and (
                    lookup[prefix + "_mean"] is None
                ) != (value == 1.0):
                    raise ValueError("missingness contradicts mean value")
            elif value is not None and not lineage:
                raise ValueError("observed feature requires lineage")
            elif value is None and lineage:
                raise ValueError("missing feature cannot claim usable lineage")
        if lookup["exercise_active_latest"] not in (None, 0.0, 1.0) or lookup[
            "fatigue_self_report_latest"
        ] not in (None, 0.0, 1.0, 2.0):
            raise ValueError("unsupported categorical encoding")
        return self


class ThresholdPolicy(Contract):
    """Alternatives only; no policy is implicitly selected or approved."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    policy_id: Identifier
    model_artifact_sha256: Digest
    derivation_manifest_sha256: Digest
    method: Literal[
        "published_estimator_offset",
        "local_training_quantile",
        "exploratory_calibration",
    ]
    threshold: Finite
    comparison: Literal["greater_than", "greater_or_equal"]
    derivation_reference: Text
    approval_reference: Text | None = None
    quantile: Annotated[Finite, Field(gt=0, lt=1)] | None = None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        expected = (
            "greater_or_equal"
            if self.method == "exploratory_calibration"
            else "greater_than"
        )
        if self.comparison != expected:
            raise ValueError("comparison contradicts named policy")
        if (self.method == "local_training_quantile") != (self.quantile is not None):
            raise ValueError("local training quantile must be explicit")
        return self

    def decide(self, score: float) -> bool | None:
        from math import isfinite

        if not isfinite(score):
            raise ValueError("decision requires finite score")
        if self.approval_reference is None:
            return None
        return (
            score >= self.threshold
            if self.comparison == "greater_or_equal"
            else score > self.threshold
        )


class ModelBMetadata(Contract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    model_id: Literal["model-b-synthetic-isolation-forest"] = (
        "model-b-synthetic-isolation-forest"
    )
    model_version: Identifier
    artifact_sha256: Digest
    training_manifest_sha256: Digest
    feature_order: tuple[Identifier, ...]
    units: tuple[str, ...]
    imputation_medians: tuple[Finite, ...]
    preprocessing: Literal["median_training_only_no_scaling"] = (
        "median_training_only_no_scaling"
    )
    score_definition: Literal["negative_sklearn_score_samples"] = (
        "negative_sklearn_score_samples"
    )
    runtime_versions: dict[str, str]
    estimator_parameters: dict[str, str | int | float | bool]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.feature_order != FEATURE_ORDER
            or self.units != FEATURE_UNITS
            or len(self.imputation_medians) != 16
        ):
            raise ValueError("incompatible artifact feature/preprocessing metadata")
        expected: dict[str, str | int | float | bool] = {
            "max_features": 1.0,
            "bootstrap": False,
            "contamination": "auto",
            "n_jobs": 1,
        }
        if any(self.estimator_parameters.get(k) != v for k, v in expected.items()):
            raise ValueError("incompatible Isolation Forest parameters")
        for key in ("n_estimators", "max_samples", "random_state"):
            value = self.estimator_parameters.get(key)
            if type(value) is not int or value < (0 if key == "random_state" else 1):
                raise ValueError("explicit positive estimator configuration required")
        if set(self.runtime_versions) != {
            "python",
            "numpy",
            "scipy",
            "scikit-learn",
            "joblib",
        }:
            raise ValueError("complete artifact runtime identity required")
        return self


class ModelBFinding(Contract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    sample: ModelBInput
    model: ModelBMetadata | None
    policy: ThresholdPolicy | None
    metadata_sha256: Digest | None
    evidence_availability_scope: Literal["careyonda_replay", "declared_source_stream"]
    anomaly_score: Finite | None
    flagged: StrictBool | None
    status: Literal["flagged", "not_flagged", "unassessed", "abstained"]
    imputed_features: Ids
    imputation_values: tuple[Finite | None, ...]
    reasons: Ids
    limitations: tuple[str, ...] = LIMITATIONS + (
        "Threshold approval is not established by this software.",
    )
    safety_status: Literal["not_evaluated"] = "not_evaluated"

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (
            self.model is not None
            and self.policy is not None
            and self.policy.model_artifact_sha256 != self.model.artifact_sha256
        ):
            raise ValueError("threshold policy and model artifact differ")
        if (self.model is None) != (self.metadata_sha256 is None):
            raise ValueError("model and metadata manifest digest must coexist")
        expected_scope = (
            "careyonda_replay"
            if self.sample.availability_mode == "retrospective"
            else "declared_source_stream"
        )
        if self.evidence_availability_scope != expected_scope:
            raise ValueError(
                "replay cannot be relabelled as prospective source evidence"
            )
        if len(self.imputation_values) != 16:
            raise ValueError("explicit sixteen-slot imputation metadata required")
        if self.status == "abstained":
            if (
                self.anomaly_score is not None
                or self.flagged is not None
                or not self.reasons
                or self.imputed_features
                or any(v is not None for v in self.imputation_values)
            ):
                raise ValueError("abstention requires null score/decision and reasons")
        else:
            if self.anomaly_score is None or self.model is None:
                raise ValueError("scored result requires model provenance")
            expected = self.policy.decide(self.anomaly_score) if self.policy else None
            expected_status = (
                "unassessed"
                if expected is None
                else ("flagged" if expected else "not_flagged")
            )
            if self.flagged != expected or self.status != expected_status:
                raise ValueError("result contradicts explicit threshold policy")
            if (self.status == "unassessed") != bool(self.reasons):
                raise ValueError("unassessed decision requires limitation reasons")
            missing = tuple(
                name
                for name, value in zip(FEATURE_ORDER, self.sample.values, strict=True)
                if value is None
            )
            if self.imputed_features != missing:
                raise ValueError("imputation must preserve original missingness")
            expected_values = tuple(
                self.model.imputation_medians[i] if value is None else None
                for i, value in enumerate(self.sample.values)
            )
            if self.imputation_values != expected_values:
                raise ValueError("imputation must use training-fitted medians")
        return self


@dataclass(frozen=True)
class VerifiedModelB:
    """Metadata consistency checked against independently supplied trust pins.

    Not a loader or proof of fitted-estimator equivalence; composition must bind
    an independently verified scorer to these bytes before real inference.
    """

    metadata: ModelBMetadata
    metadata_sha256: str
