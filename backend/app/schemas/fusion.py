"""Temporal evidence declarations and consistency checks; no join algorithm."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import model_validator

from app.schemas.baseline import (
    AvailabilityMode,
    ExcludedEvidence,
    Ids,
    Positive,
    ResearchContract,
    ResearchEvidence,
    ResearchTime,
    Text,
    TimeInterval,
    Version,
    unique_ids,
)
from app.schemas.observation import (
    METRIC_REGISTRY,
    CompartmentScope,
    Contract,
    Identifier,
    QualityStatus,
    SpacecraftScope,
)


class SourceRequirement(Contract):
    requirement_id: Identifier
    dataset_id: Identifier
    run_id: Identifier
    source_id: Identifier
    sensor_id: Identifier | None
    sensor_epoch: Identifier | None
    data_origin: Literal["synthetic", "real", "unknown"]
    compatibility: Literal["exact_identity", "unavailable"]
    metric: Identifier
    unit: Text
    maximum_age_seconds: Positive

    @model_validator(mode="after")
    def valid_requirement(self) -> Self:
        definition = METRIC_REGISTRY.get(self.metric)
        if definition is None or self.unit != (definition.canonical_unit or "1"):
            raise ValueError("source requires known metric and canonical unit")
        if (self.sensor_id is None) != (self.sensor_epoch is None):
            raise ValueError("sensor identity and epoch must be supplied together")
        if self.compatibility == "exact_identity" and (
            self.data_origin == "unknown" or self.sensor_id is None
        ):
            raise ValueError("exact compatibility requires known origin and sensor")
        return self

    def matches(self, evidence: ResearchEvidence) -> bool:
        obs = evidence.observation
        return (
            self.compatibility == "exact_identity"
            and self.dataset_id == evidence.dataset_id
            and self.run_id == evidence.run_id
            and self.source_id == obs.provenance.source_id
            and self.sensor_id == evidence.sensor_id
            and self.sensor_epoch == evidence.sensor_epoch
            and self.data_origin == evidence.data_origin
            and self.metric == obs.metric
        )


class FusionPolicy(ResearchContract):
    policy_id: Identifier
    policy_version: Version
    event_window: TimeInterval
    sources: tuple[SourceRequirement, ...]
    maximum_cross_source_separation_seconds: Positive
    context_matching: Literal["exact_mission_subject_location"]
    subject_compartment_association: Literal["required", "unavailable"]
    unit_compatibility: Literal["canonical_only_no_conversion"]
    eligible_quality: tuple[QualityStatus, ...]
    missing_treatment: Literal["abstain"]
    conflict_treatment: Literal["abstain"]
    availability_mode: AvailabilityMode

    @model_validator(mode="after")
    def valid_policy(self) -> Self:
        if self.event_window.start >= self.event_window.end:
            raise ValueError("fusion event window must have positive duration")
        if not self.sources:
            raise ValueError("fusion requires explicit source requirements")
        unique_ids(tuple(s.requirement_id for s in self.sources))
        identities = {
            (s.dataset_id, s.run_id, s.source_id, s.sensor_id, s.sensor_epoch, s.metric)
            for s in self.sources
        }
        if len(identities) != len(self.sources):
            raise ValueError("source requirements must not be ambiguous duplicates")
        if not self.eligible_quality or not set(self.eligible_quality) <= {
            "valid",
            "suspect",
        }:
            raise ValueError("only explicitly eligible valid/suspect quality is usable")
        unique_ids(self.eligible_quality)
        return self


class SubjectCompartmentAssociation(Contract):
    subject_id: Identifier
    spacecraft_id: Identifier
    compartment_id: Identifier
    interval: TimeInterval
    evidence_ids: Ids
    source_reference: Text

    @model_validator(mode="after")
    def supported_association(self) -> Self:
        if not self.evidence_ids:
            raise ValueError("association requires explicit supporting evidence")
        return self


class TemporalEvidenceGroup(ResearchContract):
    group_id: Identifier
    policy: FusionPolicy
    anchor_id: Identifier
    anchor_time: ResearchTime
    assessed_at: ResearchTime
    mission_id: Identifier
    subject_id: Identifier
    spacecraft_id: Identifier
    compartment_id: Identifier
    association: SubjectCompartmentAssociation | None
    included: tuple[ResearchEvidence, ...]
    excluded: tuple[ExcludedEvidence, ...]
    conflicting: tuple[ExcludedEvidence, ...]
    missing_requirement_ids: Ids
    reason_codes: Ids
    lineage_ids: Ids
    status: Literal[
        "aligned",
        "no_data",
        "insufficient_evidence",
        "conflicting_evidence",
        "unsupported",
    ]
    method_version: Identifier

    @model_validator(mode="after")
    def valid_group(self) -> Self:
        p = self.policy
        if (
            self.anchor_time != p.event_window.end
            or self.assessed_at < self.anchor_time
        ):
            raise ValueError(
                "anchor must end event window; assessment cannot precede it"
            )
        ids = tuple(e.observation.observation_id for e in self.included)
        excluded_ids = tuple(
            e.evidence.observation.observation_id for e in self.excluded
        )
        conflict_ids = tuple(
            e.evidence.observation.observation_id for e in self.conflicting
        )
        unique_ids(ids + excluded_ids + conflict_ids)
        if not set(ids + excluded_ids + conflict_ids) <= set(self.lineage_ids):
            raise ValueError(
                "lineage must preserve all included/excluded/conflicting IDs"
            )
        represented: set[str] = set()
        simultaneous: dict[tuple[str, str, datetime], str] = {}
        for e in self.included:
            obs = e.observation
            matching = [s for s in p.sources if s.matches(e)]
            if len(matching) != 1:
                raise ValueError("included evidence requires one compatible source")
            requirement = matching[0]
            represented.add(requirement.requirement_id)
            key = (
                requirement.requirement_id,
                obs.scope.model_dump_json(),
                obs.timestamp,
            )
            measurement = obs.measurement.model_dump_json()
            if key in simultaneous and simultaneous[key] != measurement:
                raise ValueError("conflicting simultaneous readings require exclusion")
            simultaneous[key] = measurement
            if obs.scope.mission_id != self.mission_id:
                raise ValueError("included mission must match group")
            scope = obs.scope
            if scope.kind == "astronaut" and scope.astronaut_id != self.subject_id:
                raise ValueError("included subject must match group")
            if (
                isinstance(scope, (SpacecraftScope, CompartmentScope))
                and scope.spacecraft_id != self.spacecraft_id
            ):
                raise ValueError("included spacecraft must match group")
            if (
                scope.kind == "compartment"
                and scope.compartment_id != self.compartment_id
            ):
                raise ValueError("included compartment must match group")
            if not p.event_window.start < obs.timestamp <= self.anchor_time:
                raise ValueError("included event must lie in (window start, anchor]")
            if (
                e.temporal_support.start <= p.event_window.start
                or e.temporal_support.end > self.anchor_time
            ):
                raise ValueError(
                    "temporal support must fit event window; no interpolation"
                )
            if (
                self.anchor_time - obs.timestamp
            ).total_seconds() > requirement.maximum_age_seconds:
                raise ValueError("included source exceeds its maximum age")
            if not e.available_at(self.assessed_at, p.availability_mode):
                raise ValueError("included source unavailable at prospective decision")
            if obs.quality.status not in p.eligible_quality:
                raise ValueError("included quality is not eligible")
        origins = {e.data_origin for e in self.included}
        if "unknown" in origins or len(origins) > 1:
            raise ValueError(
                "real/synthetic/unknown origins cannot form a paired group"
            )
        times = [e.observation.timestamp for e in self.included]
        if (
            times
            and (max(times) - min(times)).total_seconds()
            > p.maximum_cross_source_separation_seconds
        ):
            raise ValueError("included evidence exceeds cross-source separation")
        for item in self.conflicting:
            represented.update(
                s.requirement_id for s in p.sources if s.matches(item.evidence)
            )
        missing = {s.requirement_id for s in p.sources} - represented
        if set(self.missing_requirement_ids) != missing:
            raise ValueError("missing requirements must match unrepresented sources")
        needs_association = any(
            e.observation.scope.kind == "astronaut" for e in self.included
        ) and any(e.observation.scope.kind != "astronaut" for e in self.included)
        if needs_association:
            a = self.association
            if p.subject_compartment_association != "required" or a is None:
                raise ValueError(
                    "subject/environment pairing requires association evidence"
                )
            if (a.subject_id, a.spacecraft_id, a.compartment_id) != (
                self.subject_id,
                self.spacecraft_id,
                self.compartment_id,
            ):
                raise ValueError("association must match group context")
            supports = [e.temporal_support for e in self.included]
            if a.interval.start > min(
                s.start for s in supports
            ) or a.interval.end < max(s.end for s in supports):
                raise ValueError("association must cover all included temporal support")
        elif self.association is not None:
            a = self.association
            if (a.subject_id, a.spacecraft_id, a.compartment_id) != (
                self.subject_id,
                self.spacecraft_id,
                self.compartment_id,
            ):
                raise ValueError("association must match group context")
        if (self.status == "aligned") == bool(self.reason_codes):
            raise ValueError("only aligned groups may omit limitation reasons")
        if self.status == "aligned" and (
            missing or self.conflicting or not self.included
        ):
            raise ValueError("aligned requires complete, non-conflicting evidence")
        if self.status == "no_data" and (self.included or self.conflicting):
            raise ValueError("no_data cannot carry usable or conflicting evidence")
        if self.status == "insufficient_evidence" and (
            not self.included or not missing or self.conflicting
        ):
            raise ValueError(
                "insufficient_evidence requires partial, non-conflicting coverage"
            )
        if (
            self.conflicting
            and self.status not in {"conflicting_evidence", "unsupported"}
        ) or (not self.conflicting and self.status == "conflicting_evidence"):
            raise ValueError("conflicting evidence requires explicit conflict status")
        if (
            any(s.compatibility == "unavailable" for s in p.sources)
            and self.status != "unsupported"
        ):
            raise ValueError(
                "unavailable source compatibility requires unsupported status"
            )
        return self
