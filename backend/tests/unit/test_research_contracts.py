"""Synthetic contract checks, not algorithm or medical validation."""

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.ai.hazard_reasoning import investigate
from app.schemas.anomaly import AnomalyFinding, AnomalyPolicy
from app.schemas.baseline import BaselinePolicy, BaselineProfile, ResearchEvidence
from app.schemas.fusion import FusionPolicy, TemporalEvidenceGroup
from simulator.mission_generator import SimulationConfig, generate_mission

START = datetime(2026, 11, 13, tzinfo=UTC)


def evidence(index: int = 1) -> ResearchEvidence:
    timestamp = START + timedelta(seconds=index * 60)
    return ResearchEvidence.model_validate(
        {
            "dataset_id": "synthetic-dataset",
            "run_id": "synthetic-run",
            "sensor_id": "synthetic-sensor",
            "sensor_epoch": "epoch-1",
            "data_origin": "synthetic",
            "temporal_support": {"start": timestamp, "end": timestamp},
            "observation": {
                "schema_version": "1.0.0",
                "observation_id": f"synthetic-obs-{index}",
                "timestamp": timestamp,
                "ingested_at": timestamp + timedelta(seconds=1),
                "domain": "physiological",
                "metric": "heart_rate",
                "scope": {
                    "kind": "astronaut",
                    "astronaut_id": "synthetic-crew",
                    "mission_id": "synthetic-mission",
                },
                "measurement": {
                    "kind": "numeric",
                    "value": 70.0 + index,
                    "unit": "bpm",
                },
                "quality": {"status": "valid"},
                "provenance": {
                    "source_type": "simulator",
                    "source_id": "synthetic-source",
                    "method": "synthetic-fixture",
                    "origin": "simulated",
                    "simulation": {
                        "scenario_id": "synthetic-test",
                        "run_id": "synthetic-run",
                        "generator_version": "test-1",
                        "seed": 42,
                    },
                },
            },
        }
    )


def baseline_policy() -> BaselinePolicy:
    return BaselinePolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "synthetic-baseline-policy",
            "policy_version": "1.0.0",
            "source_scope": {
                "dataset_id": "synthetic-dataset",
                "run_id": "synthetic-run",
                "mission_id": "synthetic-mission",
                "subject_id": "synthetic-crew",
                "source_id": "synthetic-source",
                "sensor_id": "synthetic-sensor",
                "sensor_epoch": "epoch-1",
                "data_origin": "synthetic",
            },
            "metric": "heart_rate",
            "unit": "bpm",
            "reference_interval": {
                "start": START,
                "end": START + timedelta(seconds=120),
            },
            "bin_duration_seconds": 60.0,
            "minimum_occupied_bins": 2,
            "minimum_observed_span_seconds": 60.0,
            "minimum_occupancy_fraction": 1.0,
            "maximum_gap_seconds": 60.0,
            "maximum_reference_age_seconds": 600.0,
            "source_sensor_compatibility": "exact_identity",
            "availability_mode": "retrospective",
        }
    )


def profile() -> BaselineProfile:
    return BaselineProfile.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "profile_id": "synthetic-profile",
            "policy": baseline_policy(),
            "assessed_at": START + timedelta(seconds=121),
            "included": [evidence(1), evidence(2)],
            "excluded": [],
            "summary": {
                "total_bins": 2,
                "occupied_bins": 2,
                "sample_count": 2,
                "occupancy_fraction": 1.0,
                "observed_span_seconds": 60.0,
                "maximum_gap_seconds": 60.0,
                "bins": [
                    {"index": 0, "observation_ids": ["synthetic-obs-1"]},
                    {"index": 1, "observation_ids": ["synthetic-obs-2"]},
                ],
            },
            "median_value": 71.5,
            "raw_mad": 0.5,
            "status": "ready",
            "abstention_reasons": [],
            "method_version": "synthetic-declaration-1",
        }
    )


def anomaly_policy() -> AnomalyPolicy:
    return AnomalyPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "synthetic-anomaly-policy",
            "policy_version": "1.0.0",
            "metric": "heart_rate",
            "unit": "bpm",
            "score_definition": "absolute_deviation_over_raw_mad",
            "threshold_governance": "unassessed",
            "governance_source": "Synthetic contract fixture; no approved threshold",
            "calibration": None,
            "threshold": None,
        }
    )


def finding() -> AnomalyFinding:
    return AnomalyFinding.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "finding_id": "synthetic-finding",
            "policy": anomaly_policy(),
            "baseline": profile(),
            "evidence": evidence(3),
            "assessed_at": START + timedelta(seconds=181),
            "original_value": 73.0,
            "signed_deviation": 1.5,
            "absolute_deviation": 1.5,
            "raw_mad_score": 3.0,
            "direction": "above",
            "score_status": "scored",
            "threshold_status": "unassessed",
            "evidence_ids": ["synthetic-obs-3"],
            "profile_lineage_ids": ["synthetic-profile"],
            "quality_limitations": [],
            "explanation": "Synthetic declared deviation; no medical interpretation.",
            "abstention_reasons": [],
            "method_version": "synthetic-declaration-1",
        }
    )


def fusion_policy() -> FusionPolicy:
    return FusionPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "synthetic-fusion-policy",
            "policy_version": "1.0.0",
            "event_window": {"start": START, "end": START + timedelta(seconds=180)},
            "sources": [
                {
                    "requirement_id": "hr",
                    "dataset_id": "synthetic-dataset",
                    "run_id": "synthetic-run",
                    "source_id": "synthetic-source",
                    "sensor_id": "synthetic-sensor",
                    "sensor_epoch": "epoch-1",
                    "data_origin": "synthetic",
                    "compatibility": "exact_identity",
                    "metric": "heart_rate",
                    "unit": "bpm",
                    "maximum_age_seconds": 120.0,
                }
            ],
            "maximum_cross_source_separation_seconds": 120.0,
            "context_matching": "exact_mission_subject_location",
            "subject_compartment_association": "required",
            "unit_compatibility": "canonical_only_no_conversion",
            "eligible_quality": ["valid"],
            "missing_treatment": "abstain",
            "conflict_treatment": "abstain",
            "availability_mode": "retrospective",
        }
    )


def group() -> TemporalEvidenceGroup:
    return TemporalEvidenceGroup.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "group_id": "synthetic-group",
            "policy": fusion_policy(),
            "anchor_id": "synthetic-anchor",
            "anchor_time": START + timedelta(seconds=180),
            "assessed_at": START + timedelta(seconds=181),
            "mission_id": "synthetic-mission",
            "subject_id": "synthetic-crew",
            "spacecraft_id": "synthetic-ship",
            "compartment_id": "synthetic-cabin",
            "association": None,
            "included": [evidence(1), evidence(2)],
            "excluded": [],
            "conflicting": [],
            "missing_requirement_ids": [],
            "reason_codes": [],
            "lineage_ids": ["synthetic-obs-1", "synthetic-obs-2"],
            "status": "aligned",
            "method_version": "synthetic-declaration-1",
        }
    )


@pytest.mark.parametrize(
    "factory", [baseline_policy, profile, anomaly_policy, finding, fusion_policy, group]
)
def test_roundtrip_and_strict_extra(factory: Callable[[], BaseModel]) -> None:
    model: BaseModel = factory()
    assert type(model).model_validate_json(model.model_dump_json()) == model
    data = model.model_dump()
    data["schema_version"] = "2.0.0"
    with pytest.raises(ValidationError):
        type(model).model_validate(data)
    data = model.model_dump()
    data["unexpected"] = "rejected"
    with pytest.raises(ValidationError):
        type(model).model_validate(data)


@pytest.mark.parametrize("value", ["2026-11-13T00:00:00", 1794528000, True])
def test_timezone_required(value: object) -> None:
    data = profile().model_dump()
    data["assessed_at"] = value
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)


def test_utc_normalization_and_numeric_strictness() -> None:
    data = profile().model_dump()
    data["assessed_at"] = "2026-11-13T02:02:01+02:00"
    assert BaselineProfile.model_validate(data).assessed_at == START + timedelta(
        seconds=121
    )
    for value in ["0.5", True, float("inf"), float("nan"), -1.0]:
        data["raw_mad"] = value
        with pytest.raises(ValidationError):
            BaselineProfile.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bin_duration_seconds", 0.0),
        ("bin_duration_seconds", 121.0),
        ("minimum_occupied_bins", 3),
        ("minimum_occupied_bins", True),
        ("minimum_observed_span_seconds", 121.0),
        ("minimum_occupancy_fraction", 0.0),
        ("minimum_occupancy_fraction", 1.1),
        ("maximum_gap_seconds", -1.0),
        ("maximum_reference_age_seconds", float("inf")),
        ("unit", "ppm"),
        ("metric", "sleep_state"),
        ("policy_version", "latest"),
    ],
)
def test_policy_bounds(field: str, value: object) -> None:
    data = baseline_policy().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        BaselinePolicy.model_validate(data)


def test_ordered_reference_and_explicit_fields() -> None:
    data = baseline_policy().model_dump()
    data["reference_interval"]["start"] = START + timedelta(seconds=121)
    with pytest.raises(ValidationError):
        BaselinePolicy.model_validate(data)
    for name in [
        "minimum_occupancy_fraction",
        "maximum_gap_seconds",
        "maximum_reference_age_seconds",
        "availability_mode",
    ]:
        data = baseline_policy().model_dump()
        del data[name]
        with pytest.raises(ValidationError):
            BaselinePolicy.model_validate(data)


@pytest.mark.parametrize(
    "field",
    [
        "sensor_id",
        "sensor_epoch",
        "subject_id",
        "mission_id",
        "dataset_id",
        "run_id",
        "source_id",
    ],
)
def test_profile_scope_isolation(field: str) -> None:
    data = profile().model_dump()
    data["policy"]["source_scope"][field] = "different"
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "empty",
        "overlap",
        "count",
        "bin",
        "fraction",
        "nonfinite",
        "bad_quality",
        "flat_ready",
        "null_ready",
    ],
)
def test_profile_invalid_lineage_and_statistics(mutation: str) -> None:
    data = profile().model_dump()
    if mutation == "duplicate":
        data["included"] = [data["included"][0], data["included"][0]]
    elif mutation == "empty":
        data["included"][0]["observation"]["observation_id"] = ""
    elif mutation == "overlap":
        data["excluded"] = [
            {"evidence": data["included"][0], "reason_codes": ["synthetic-exclusion"]}
        ]
    elif mutation == "count":
        data["summary"]["sample_count"] = 3
    elif mutation == "bin":
        data["summary"]["bins"][0]["index"] = 1
    elif mutation == "fraction":
        data["summary"]["occupancy_fraction"] = 0.5
    elif mutation == "nonfinite":
        data["median_value"] = float("nan")
    elif mutation == "bad_quality":
        data["included"][0]["observation"]["quality"] = {
            "status": "suspect",
            "reason_codes": ["synthetic-suspect"],
        }
    elif mutation == "flat_ready":
        data["raw_mad"] = 0.0
    else:
        data["raw_mad"] = data["median_value"] = None
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)


def test_flat_and_sparse_reference_abstain() -> None:
    data = profile().model_dump()
    data.update(raw_mad=0.0, status="flat_reference", abstention_reasons=["zero_mad"])
    flat = BaselineProfile.model_validate(data)
    f = finding().model_dump()
    f.update(
        baseline=flat,
        score_status="flat_reference",
        raw_mad_score=None,
        abstention_reasons=["zero_mad"],
    )
    assert AnomalyFinding.model_validate(f).raw_mad_score is None
    f["raw_mad_score"] = 0.0
    with pytest.raises(ValidationError):
        AnomalyFinding.model_validate(f)
    data = profile().model_dump()
    data.update(
        included=[],
        median_value=None,
        raw_mad=None,
        status="insufficient_reference",
        abstention_reasons=["sparse_reference"],
    )
    data["summary"].update(
        occupied_bins=0,
        sample_count=0,
        occupancy_fraction=0.0,
        observed_span_seconds=0.0,
        maximum_gap_seconds=0.0,
        bins=[],
    )
    sparse = BaselineProfile.model_validate(data)
    f.update(
        baseline=sparse,
        score_status="insufficient_reference",
        raw_mad_score=None,
        signed_deviation=None,
        absolute_deviation=None,
        direction="unassessed",
        abstention_reasons=["sparse_reference"],
    )
    assert AnomalyFinding.model_validate(f).direction == "unassessed"


def test_unknown_compatibility_requires_unsupported() -> None:
    data = profile().model_dump()
    data["policy"]["source_sensor_compatibility"] = "unavailable"
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)
    data.update(
        status="unsupported",
        median_value=None,
        raw_mad=None,
        abstention_reasons=["compatibility_unknown"],
    )
    assert BaselineProfile.model_validate(data).status == "unsupported"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("raw_mad_score", None),
        ("raw_mad_score", 4.0),
        ("raw_mad_score", float("inf")),
        ("signed_deviation", -1.5),
        ("absolute_deviation", 1.0),
        ("direction", "below"),
        ("threshold_status", "exceeded"),
        ("evidence_ids", []),
        ("profile_lineage_ids", []),
        ("evidence_ids", ["synthetic-obs-3", "synthetic-obs-3"]),
    ],
)
def test_invalid_anomaly(field: str, value: object) -> None:
    data = finding().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        AnomalyFinding.model_validate(data)


def test_sensor_mismatch_and_unavailable_target() -> None:
    data = finding().model_dump()
    data["evidence"]["sensor_epoch"] = "different"
    with pytest.raises(ValidationError):
        AnomalyFinding.model_validate(data)
    data.update(
        score_status="unsupported",
        signed_deviation=None,
        absolute_deviation=None,
        raw_mad_score=None,
        direction="unassessed",
        abstention_reasons=["sensor_mismatch"],
    )
    assert AnomalyFinding.model_validate(data).score_status == "unsupported"
    data = finding().model_dump()
    data["evidence"]["observation"].update(
        measurement={"kind": "unavailable", "reason": "not_received"},
        quality={"status": "missing", "reason_codes": ["not_received"]},
    )
    data.update(
        original_value=None,
        signed_deviation=None,
        absolute_deviation=None,
        raw_mad_score=None,
        direction="unassessed",
        score_status="unsupported",
        quality_limitations=["not_received"],
        abstention_reasons=["missing_observation"],
    )
    assert AnomalyFinding.model_validate(data).original_value is None


def test_approved_research_threshold_requires_governance_and_artifact() -> None:
    data = finding().model_dump()
    calibration = {
        "artifact_id": "synthetic-calibration",
        "artifact_version": "1.0.0",
        "source": "Synthetic test artifact, no clinical validity",
    }
    threshold = {
        "value": 3.0,
        "comparison": "greater_than_or_equal",
        "approval_reference": "Synthetic test approval only",
        "approved_at": START,
        "calibration": calibration,
    }
    data["policy"].update(calibration=calibration, threshold=threshold)
    with pytest.raises(ValidationError):
        AnomalyFinding.model_validate(data)
    data["policy"]["threshold_governance"] = "approved_research"
    data["threshold_status"] = "exceeded"
    assert AnomalyFinding.model_validate(data).threshold_status == "exceeded"
    data["policy"]["threshold"]["comparison"] = "greater_than"
    data["threshold_status"] = "not_exceeded"
    assert AnomalyFinding.model_validate(data).threshold_status == "not_exceeded"
    data["policy"]["calibration"] = None
    with pytest.raises(ValidationError):
        AnomalyFinding.model_validate(data)


@pytest.mark.parametrize("kind", ["profile", "finding", "group"])
def test_prospective_availability(kind: str) -> None:
    model = {"profile": profile, "finding": finding, "group": group}[kind]()
    data = model.model_dump()
    if kind == "profile":
        data["policy"]["availability_mode"] = "prospective"
        target = data["included"][0]["observation"]
    elif kind == "finding":
        data["baseline"]["policy"]["availability_mode"] = "prospective"
        target = data["evidence"]["observation"]
    else:
        data["policy"]["availability_mode"] = "prospective"
        target = data["included"][0]["observation"]
    for unavailable in [None, START + timedelta(seconds=1000)]:
        target["ingested_at"] = unavailable
        with pytest.raises(ValidationError):
            type(model).model_validate(data)
    target["ingested_at"] = data["assessed_at"]
    assert type(model).model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    [
        "lower_boundary",
        "future",
        "age",
        "separation",
        "mission",
        "subject",
        "unit",
        "duplicate",
        "support",
        "unknown_compatibility",
    ],
)
def test_fusion_invalid_alignment(mutation: str) -> None:
    data = group().model_dump()
    if mutation == "lower_boundary":
        data["policy"]["event_window"]["start"] = START + timedelta(seconds=60)
    elif mutation == "future":
        data["anchor_time"] = START + timedelta(seconds=100)
    elif mutation == "age":
        data["policy"]["sources"][0]["maximum_age_seconds"] = 119.0
    elif mutation == "separation":
        data["policy"]["maximum_cross_source_separation_seconds"] = 59.0
    elif mutation == "mission":
        data["mission_id"] = "different"
    elif mutation == "subject":
        data["subject_id"] = "different"
    elif mutation == "unit":
        data["policy"]["sources"][0]["unit"] = "Pa"
    elif mutation == "duplicate":
        data["included"] = data["included"] + data["included"]
    elif mutation == "support":
        data["included"][0]["temporal_support"]["start"] = START - timedelta(days=1)
    else:
        data["policy"]["sources"][0]["compatibility"] = "unavailable"
    with pytest.raises(ValidationError):
        TemporalEvidenceGroup.model_validate(data)


def test_event_upper_and_age_boundaries_are_inclusive() -> None:
    data = group().model_dump()
    data["included"] = [evidence(1).model_dump(), evidence(3).model_dump()]
    data["lineage_ids"] = ["synthetic-obs-1", "synthetic-obs-3"]
    assert TemporalEvidenceGroup.model_validate(data).status == "aligned"


def test_no_data_conflict_and_missing_states() -> None:
    data = group().model_dump()
    excluded = [
        {"evidence": e, "reason_codes": ["synthetic-conflict"]}
        for e in data["included"]
    ]
    data.update(
        included=[],
        conflicting=excluded,
        reason_codes=["conflicting_evidence"],
        status="conflicting_evidence",
    )
    assert TemporalEvidenceGroup.model_validate(data).conflicting
    data["status"] = "aligned"
    with pytest.raises(ValidationError):
        TemporalEvidenceGroup.model_validate(data)
    data.update(
        conflicting=[],
        excluded=excluded,
        missing_requirement_ids=["hr"],
        status="no_data",
        reason_codes=["no_usable_evidence"],
    )
    assert TemporalEvidenceGroup.model_validate(data).status == "no_data"
    data["missing_requirement_ids"] = []
    with pytest.raises(ValidationError):
        TemporalEvidenceGroup.model_validate(data)


def paired_group(real: bool = False) -> dict[str, Any]:
    data = group().model_dump()
    environmental = evidence(2).model_dump()
    obs = environmental["observation"]
    obs.update(
        observation_id="synthetic-env",
        domain="environmental",
        metric="cabin_co2_partial_pressure",
        measurement={"kind": "numeric", "value": 50.0, "unit": "Pa"},
        scope={
            "kind": "compartment",
            "mission_id": "synthetic-mission",
            "spacecraft_id": "synthetic-ship",
            "compartment_id": "synthetic-cabin",
        },
    )
    obs["provenance"]["source_id"] = "environment-source"
    if real:
        environmental["data_origin"] = "real"
        obs["provenance"] = {
            "source_type": "sensor",
            "source_id": "environment-source",
            "method": "synthetic-test-real-origin",
            "origin": "measured",
        }
    requirement = deepcopy(data["policy"]["sources"][0])
    requirement.update(
        requirement_id="co2",
        source_id="environment-source",
        metric="cabin_co2_partial_pressure",
        unit="Pa",
        data_origin="real" if real else "synthetic",
    )
    data["policy"]["sources"] = [*data["policy"]["sources"], requirement]
    data["included"] = [*data["included"], environmental]
    data["lineage_ids"] = [*data["lineage_ids"], "synthetic-env"]
    data["association"] = {
        "subject_id": "synthetic-crew",
        "spacecraft_id": "synthetic-ship",
        "compartment_id": "synthetic-cabin",
        "interval": {"start": START, "end": START + timedelta(seconds=180)},
        "evidence_ids": ["synthetic-association"],
        "source_reference": "Explicit synthetic occupancy fixture",
    }
    return data


def test_subject_compartment_association_and_unsupported_source_pairing() -> None:
    data = paired_group()
    assert TemporalEvidenceGroup.model_validate(data).status == "aligned"
    data["association"] = None
    with pytest.raises(ValidationError):
        TemporalEvidenceGroup.model_validate(data)
    data = paired_group(real=True)
    with pytest.raises(ValidationError):
        TemporalEvidenceGroup.model_validate(data)
    unpaired = data["included"].pop()
    data.update(
        excluded=[{"evidence": unpaired, "reason_codes": ["real_synthetic_unpaired"]}],
        missing_requirement_ids=["co2"],
        status="unsupported",
        reason_codes=["real_synthetic_unpaired"],
    )
    assert TemporalEvidenceGroup.model_validate(data).status == "unsupported"
    data["status"] = "insufficient_evidence"
    assert TemporalEvidenceGroup.model_validate(data).status == "insufficient_evidence"


def test_m2_contract_regression() -> None:
    reference = generate_mission(
        SimulationConfig(
            steps=3,
            episodes_per_scenario=1,
            noise_scale=0,
            missing_probability=0,
            start=datetime(2026, 11, 12, 23, tzinfo=UTC),
        )
    )
    current = generate_mission(
        SimulationConfig(
            steps=3, episodes_per_scenario=1, noise_scale=0, missing_probability=0
        )
    )
    ref_anchor = next(
        a
        for a in reversed(reference.anchors)
        if reference.labels[a.sample_id] == "baseline"
    )
    snapshots = []
    for name in ["baseline", "elevated_co2", "sleep_deprivation", "recent_exercise"]:
        anchor = next(
            a for a in reversed(current.anchors) if current.labels[a.sample_id] == name
        )
        result = investigate(
            current.observations, anchor, reference.observations, ref_anchor
        )
        assert result.selected_hypothesis == name
        assert result.safety_status == "not_evaluated"
        before = result.model_dump_json()
        # Research declarations are sidecars; no M2 input/output or inference hook.
        profile(), finding(), group()
        assert (
            investigate(
                current.observations, anchor, reference.observations, ref_anchor
            ).model_dump_json()
            == before
        )
        snapshots.append(sha256(before.encode()).hexdigest())
    assert snapshots == M2_SNAPSHOTS


M2_SNAPSHOTS = [
    "02d29b7c4274329859b187475cd9b3c412685c299eb1f2289730e87e4cb1ccfe",
    "497cb189f366e161ea21f371f27b483a14a5008ea72d4f10f348b2315290fbfd",
    "07b2aac16b314785d74387206ea82801922cdbe4e56e5ffccdaa51a45a99c102",
    "2def4cb61fa021a36180aded03e8a0999ff9d6307b3b2cb1eadd1ffc889a7867",
]


@pytest.mark.parametrize("factory", [profile, group])
def test_simultaneous_conflicts_cannot_be_included(
    factory: Callable[[], BaseModel],
) -> None:
    model = factory()
    data = model.model_dump()
    duplicate = deepcopy(data["included"][0])
    duplicate["observation"]["observation_id"] = "synthetic-conflicting"
    duplicate["observation"]["measurement"]["value"] = 99.0
    data["included"] = [*data["included"], duplicate]
    if isinstance(model, BaselineProfile):
        summary = data["summary"]
        summary["sample_count"] = 3
        summary["bins"][0]["observation_ids"] = [
            "synthetic-obs-1",
            "synthetic-conflicting",
        ]
    else:
        data["lineage_ids"] = [*data["lineage_ids"], "synthetic-conflicting"]
    with pytest.raises(ValidationError, match="conflicting simultaneous"):
        type(model).model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"), [("observed_span_seconds", 59.0), ("maximum_gap_seconds", 59.0)]
)
def test_profile_declared_temporal_summary_must_match_evidence(
    field: str, value: float
) -> None:
    data = profile().model_dump()
    data["summary"][field] = value
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)


def test_freshness_and_availability_at_reference_boundary() -> None:
    data = profile().model_dump()
    data["assessed_at"] = START + timedelta(seconds=720)
    assert BaselineProfile.model_validate(data).status == "ready"
    data["assessed_at"] += timedelta(microseconds=1)
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)
    data = profile().model_dump()
    data["policy"]["availability_mode"] = "prospective"
    data["assessed_at"] = START + timedelta(seconds=120)
    with pytest.raises(ValidationError):
        BaselineProfile.model_validate(data)
    data["included"][1]["observation"]["ingested_at"] = START + timedelta(seconds=120)
    assert BaselineProfile.model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_source",
        "duplicate_source",
        "invalid_quality",
        "zero_separation",
        "no_window",
        "missing_age",
    ],
)
def test_fusion_policy_requires_explicit_supported_rules(mutation: str) -> None:
    data = fusion_policy().model_dump()
    if mutation == "empty_source":
        data["sources"] = []
    elif mutation == "duplicate_source":
        data["sources"] = [*data["sources"], data["sources"][0]]
    elif mutation == "invalid_quality":
        data["eligible_quality"] = ["invalid"]
    elif mutation == "zero_separation":
        data["maximum_cross_source_separation_seconds"] = 0.0
    elif mutation == "no_window":
        data["event_window"]["start"] = data["event_window"]["end"]
    else:
        del data["sources"][0]["maximum_age_seconds"]
    with pytest.raises(ValidationError):
        FusionPolicy.model_validate(data)


def test_source_origin_provenance_and_sensor_metadata() -> None:
    data = evidence().model_dump()
    for field, value in [
        ("data_origin", "real"),
        ("sensor_epoch", None),
        ("run_id", "other-run"),
    ]:
        wrong = {**data, field: value}
        with pytest.raises(ValidationError):
            ResearchEvidence.model_validate(wrong)


def test_extreme_finite_durations_do_not_escape_validation() -> None:
    data = baseline_policy().model_dump()
    data["bin_duration_seconds"] = 5e-324
    with pytest.raises(ValidationError):
        BaselinePolicy.model_validate(data)
    data = group().model_dump()
    data["policy"]["sources"][0]["maximum_age_seconds"] = 1e308
    assert TemporalEvidenceGroup.model_validate(data).status == "aligned"
