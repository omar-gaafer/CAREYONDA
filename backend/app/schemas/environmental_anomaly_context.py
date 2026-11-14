"""Isolated Model A research sidecars; never clinical or M4.2 findings."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, AwareDatetime, Field, model_validator

from app.schemas.observation import METRIC_REGISTRY, Contract, Identifier, Observation

Time = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
LIMITATIONS = (
    "Research only: statistical unusualness is not a diagnosis, probability, severity or hazard determination.",
    "RR-1 environment is not paired with human physiology; no exposure attribution is established.",
    "Training quantile is a review convention, not an approved clinical threshold.",
    "Availability and source provenance are caller declarations, not independently authenticated.",
    "M2 ranking, M4.2 findings and safety policies are not evaluated or modified.",
)

REPLAY_LIMITATIONS = (
    "Historical research replay: CAREYONDA acquisition does not establish availability during the NASA mission.",
    "Historical source ingestion is unknown; replay observations are not contemporary astronaut exposure evidence.",
)


class ReplayAcquisition(Contract):
    """Caller-supplied receipt of actual local acquisition, not a NASA ingestion log."""

    record_id: Identifier
    dataset_id: Identifier
    dataset_manifest_sha256: Hash
    acquired_at: Time
    source_reference: Text


class EnvironmentalScope(Contract):
    mission_id: Literal["NASA-RR1"]
    spacecraft_id: Literal["ISS"]
    data_origin: Literal["real", "synthetic"]
    dataset_id: Identifier
    run_id: Identifier


class FeatureEvidence(Contract):
    name: Identifier
    unit: Text
    value: Finite | None
    observation_ids: tuple[Identifier, ...]

    @model_validator(mode="after")
    def unique_lineage(self) -> Self:
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("duplicate feature observation IDs")
        return self


class EnvironmentalSample(Contract):
    """Caller-validated environmental features with original evidence snapshots."""

    sample_id: Identifier
    scope: EnvironmentalScope
    event_time_utc: Time
    available_at: Time | None = None
    assessment_mode: Literal["live", "historical_replay"] = "live"
    historical_source_availability: Literal["known", "unknown"] = "known"
    replay_acquired_at: Time | None = None
    replay_acquisition: ReplayAcquisition | None = None
    transformation_version: Literal["environmental-1.0.0"]
    features: tuple[FeatureEvidence, ...]
    observations: Annotated[tuple[Observation, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        expected = [
            {
                "name": f"{metric}_{suffix}",
                "unit": "1"
                if suffix in {"count_30m", "missing"}
                else METRIC_REGISTRY[metric].canonical_unit,
            }
            for metric in (
                "cabin_co2_concentration",
                "environment_temperature",
                "relative_humidity",
            )
            for suffix in ("value", "mean_30m", "delta", "count_30m", "missing")
        ] + [{"name": "gap_seconds", "unit": "s"}]
        if [(f.name, f.unit) for f in self.features] != [
            (f["name"], f["unit"]) for f in expected
        ]:
            raise ValueError(
                "exact environmental feature order and canonical units required"
            )
        if self.assessment_mode == "live":
            if self.available_at is None or self.available_at < self.event_time_utc:
                raise ValueError(
                    "live mode requires factual availability after event time"
                )
            if (
                self.historical_source_availability != "known"
                or self.replay_acquired_at is not None
                or self.replay_acquisition is not None
            ):
                raise ValueError(
                    "replay metadata cannot be represented as live evidence"
                )
        else:
            receipt = self.replay_acquisition
            if (
                self.available_at is not None
                or self.historical_source_availability != "unknown"
            ):
                raise ValueError(
                    "replay must retain unknown historical source availability"
                )
            if self.replay_acquired_at is None or receipt is None:
                raise ValueError(
                    "replay requires an actual recorded CAREYONDA acquisition"
                )
            if (
                receipt.acquired_at != self.replay_acquired_at
                or receipt.dataset_id != self.scope.dataset_id
            ):
                raise ValueError(
                    "replay receipt timestamp and dataset identity must match"
                )
            if self.replay_acquired_at < self.event_time_utc:
                raise ValueError("replay acquisition cannot precede source events")
        ids = [o.observation_id for o in self.observations]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate observation IDs")
        lookup = {o.observation_id: o for o in self.observations}
        for feature in self.features:
            if (
                feature.value is not None
                and feature.name.endswith(("_value", "_mean_30m", "_delta"))
                and not feature.observation_ids
            ):
                raise ValueError("observed feature requires lineage")
            if not set(feature.observation_ids) <= set(ids):
                raise ValueError(
                    "feature lineage must resolve to original observations"
                )
            if feature.name != "gap_seconds":
                metric = next(
                    m
                    for m in (
                        "cabin_co2_concentration",
                        "environment_temperature",
                        "relative_humidity",
                    )
                    if feature.name.startswith(m + "_")
                )
                if any(lookup[oid].metric != metric for oid in feature.observation_ids):
                    raise ValueError("feature lineage metric mismatch")
                if any(
                    not self.event_time_utc - timedelta(seconds=1800)
                    < lookup[oid].timestamp
                    <= self.event_time_utc
                    for oid in feature.observation_ids
                ):
                    raise ValueError("feature lineage outside causal window")
        for obs in self.observations:
            if (
                obs.scope.kind != "spacecraft"
                or obs.scope.mission_id != self.scope.mission_id
                or obs.scope.spacecraft_id != self.scope.spacecraft_id
            ):
                raise ValueError("observation environmental scope mismatch")
            if obs.provenance.origin not in {"measured", "simulated"}:
                raise ValueError(
                    "original environmental measurement provenance required"
                )
            if (obs.provenance.origin == "simulated") != (
                self.scope.data_origin == "synthetic"
            ):
                raise ValueError("mixed real and synthetic evidence")
            if obs.timestamp > self.event_time_utc:
                raise ValueError("future event evidence")
            if self.assessment_mode == "live":
                if (
                    obs.ingested_at is None
                    or self.available_at is None
                    or obs.ingested_at > self.available_at
                ):
                    raise ValueError("unknown or future evidence availability")
            elif obs.ingested_at is not None:
                raise ValueError("unknown historical source ingestion must remain null")
        return self

    @property
    def evidence_available_at(self) -> datetime:
        value = (
            self.available_at
            if self.assessment_mode == "live"
            else self.replay_acquired_at
        )
        assert value is not None
        return value


class ModelIdentity(Contract):
    model_id: Literal["careyonda-model-a-nasa-rr1-environment-iforest"]
    model_version: Literal["1.1.0"]
    feature_schema_version: Literal["1.0.0"]
    artifact_sha256: Hash
    dataset_manifest_sha256: Hash


class EnvironmentalAnomalyContext(Contract):
    schema_version: Literal["1.0.0", "1.1.0"] = "1.1.0"
    assessment_mode: Literal["live", "historical_replay"] = "live"
    historical_source_availability: Literal["known", "unknown"] = "known"
    replay_acquired_at: Time | None = None
    source_event_time: Time | None = None
    evidence_availability_scope: Literal["source_stream", "careyonda_replay"] = (
        "source_stream"
    )
    interpretation: Literal["research_only"] = "research_only"
    sample: EnvironmentalSample
    assessed_at: Time
    model: ModelIdentity | None
    availability: Literal["available", "unavailable"]
    compatibility: Literal["compatible", "incompatible", "unknown"]
    status: Literal["flagged", "not_flagged", "unassessed", "abstained"]
    anomaly_score: Finite | None
    threshold: Finite | None
    threshold_method: Literal["training_score_quantile"] | None
    imputed_features: tuple[Identifier, ...]
    abstention_reasons: tuple[Text, ...]
    limitations: tuple[Text, ...] = LIMITATIONS

    @model_validator(mode="after")
    def consistent(self) -> Self:
        replay = self.sample.assessment_mode == "historical_replay"
        if (
            self.assessment_mode != self.sample.assessment_mode
            or self.historical_source_availability
            != self.sample.historical_source_availability
            or self.replay_acquired_at != self.sample.replay_acquired_at
        ):
            raise ValueError("sidecar availability policy must match its source sample")
        if self.evidence_availability_scope != (
            "careyonda_replay" if replay else "source_stream"
        ):
            raise ValueError("availability scope cannot relabel replay as live")
        if self.schema_version == "1.0.0" and replay:
            raise ValueError("replay requires sidecar schema 1.1.0")
        if (
            self.source_event_time is not None
            and self.source_event_time != self.sample.event_time_utc
        ):
            raise ValueError("original mission event time must be preserved")
        if self.schema_version == "1.1.0" and self.source_event_time is None:
            raise ValueError("schema 1.1.0 requires explicit original event time")
        if replay and not set(REPLAY_LIMITATIONS) <= set(self.limitations):
            raise ValueError("replay limitations must be retained")
        if self.sample.evidence_available_at > self.assessed_at:
            raise ValueError("evidence unavailable at assessment")
        if not set(LIMITATIONS) <= set(self.limitations):
            raise ValueError("research limitations must be retained")
        names = {f.name for f in self.sample.features}
        if (
            len(set(self.imputed_features)) != len(self.imputed_features)
            or not set(self.imputed_features) <= names
        ):
            raise ValueError("invalid imputation feature lineage")
        if (self.threshold is None) != (self.threshold_method is None):
            raise ValueError("threshold and method must coexist")
        if self.model is None and (self.threshold is not None or self.imputed_features):
            raise ValueError(
                "model-free abstention cannot declare threshold or imputation"
            )
        if any(
            self.sample.features[
                next(i for i, f in enumerate(self.sample.features) if f.name == name)
            ].value
            is not None
            for name in self.imputed_features
        ):
            raise ValueError("imputation must refer to originally missing features")
        if self.status == "abstained":
            if self.anomaly_score is not None or not self.abstention_reasons:
                raise ValueError("abstention requires null score and reasons")
        else:
            if (
                self.model is None
                or self.availability != "available"
                or self.compatibility != "compatible"
                or self.anomaly_score is None
                or self.abstention_reasons
            ):
                raise ValueError(
                    "usable score requires compatible available model and no abstention"
                )
            expected = (
                "unassessed"
                if self.threshold is None
                else (
                    "flagged" if self.anomaly_score >= self.threshold else "not_flagged"
                )
            )
            if self.status != expected:
                raise ValueError("flag must match inclusive threshold comparison")
        return self
