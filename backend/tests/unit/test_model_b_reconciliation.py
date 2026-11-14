"""Synthetic contract and fake-estimator tests. No fitting or deserialization."""

from collections.abc import Sequence
from datetime import timedelta
from hashlib import sha256
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from app.ai.model_b_anomaly import (
    AcquisitionReceipt,
    ModelBBinding,
    ModelBError,
    ModelBService,
)
from app.features.temporal_features import build_features
from app.schemas.baseline import ResearchEvidence, TimeInterval
from app.schemas.model_b import (
    FEATURE_ORDER,
    FEATURE_UNITS,
    ModelBContext,
    ModelBFinding,
    ModelBInput,
    ModelBMetadata,
    ThresholdPolicy,
    VerifiedModelB,
)
from app.storage.model_b_store import ModelBArtifactError, verify_model_b_artifact
from simulator.mission_generator import SimulationConfig, generate_mission

DIGEST = "a" * 64
RUNTIME = dict.fromkeys(
    ("python", "numpy", "scipy", "scikit-learn", "joblib"), "synthetic-test"
)


def sample(*, drop_heart: bool = False, missing: bool = False) -> ModelBInput:
    mission = generate_mission(
        SimulationConfig(
            seed=42,
            steps=1,
            episodes_per_scenario=1,
            missing_probability=1.0 if missing else 0.0,
        )
    )
    anchor = mission.anchors[0]
    observations = [
        o for o in mission.observations if not (drop_heart and o.metric == "heart_rate")
    ]
    f = build_features(observations, [anchor])[0]
    observations = [
        o for o in observations if o.observation_id in f.window_observation_ids
    ]
    simulation = observations[0].provenance.simulation
    assert simulation is not None
    evidence = tuple(
        ResearchEvidence(
            observation=o,
            dataset_id="synthetic-dataset",
            run_id=simulation.run_id,
            sensor_id=None,
            sensor_epoch=None,
            data_origin="synthetic",
            temporal_support=TimeInterval(start=o.timestamp, end=o.timestamp),
        )
        for o in observations
    )
    return ModelBInput(
        dataset_manifest_sha256=DIGEST,
        dataset_id="synthetic-dataset",
        run_id=simulation.run_id,
        context=ModelBContext.model_validate(anchor.model_dump()),
        assessed_at=anchor.timestamp + timedelta(days=2),
        availability_mode="retrospective",
        acquired_at=anchor.timestamp + timedelta(days=1),
        acquisition_reference="synthetic-receipt",
        feature_order=FEATURE_ORDER,
        units=FEATURE_UNITS,
        values=tuple(f.values[n] for n in FEATURE_ORDER),
        feature_evidence_ids=tuple(f.evidence[n] for n in FEATURE_ORDER),
        window_observation_ids=f.window_observation_ids,
        evidence=evidence,
    )


def metadata() -> ModelBMetadata:
    return ModelBMetadata(
        model_version="test-1.0.0",
        artifact_sha256=sha256(b"synthetic-not-a-model").hexdigest(),
        training_manifest_sha256=DIGEST,
        feature_order=FEATURE_ORDER,
        units=FEATURE_UNITS,
        imputation_medians=(1.0,) * 16,
        runtime_versions=RUNTIME,
        estimator_parameters={
            "n_estimators": 200,
            "max_samples": 256,
            "random_state": 42,
            "max_features": 1.0,
            "bootstrap": False,
            "contamination": "auto",
            "n_jobs": 1,
        },
    )


class FakeScorer:
    def __init__(self, score: float = -0.5) -> None:
        self.score = score
        self.rows: Sequence[Sequence[float]] = ()

    def score_samples(self, values: Sequence[Sequence[float]]) -> Sequence[float]:
        self.rows = values
        return (self.score,)


def service(
    s: ModelBInput,
    *,
    scorer: FakeScorer | None = None,
    policy: ThresholdPolicy | None = None,
    receipt: bool = True,
    available: bool = True,
) -> ModelBService:
    c = s.context
    binding = ModelBBinding(
        c.mission_id,
        c.astronaut_id,
        c.spacecraft_id,
        c.compartment_id,
        s.dataset_id,
        s.run_id,
        s.dataset_manifest_sha256,
    )
    assert s.acquired_at is not None
    receipts = (
        (AcquisitionReceipt(DIGEST, s.acquired_at, "synthetic-receipt"),)
        if receipt
        else ()
    )
    return ModelBService(
        binding,
        model=VerifiedModelB(metadata(), "b" * 64) if available else None,
        scorer=(scorer or FakeScorer()) if available else None,
        receipts=receipts,
        policy=policy,
    )


def mutate(s: ModelBInput, **changes: Any) -> ModelBInput:
    return ModelBInput.model_validate({**s.model_dump(), **changes})


def test_unassessed_default_and_deterministic_roundtrip() -> None:
    s = sample()
    result = service(s).assess(s)
    assert (
        result.anomaly_score == 0.5
        and result.flagged is None
        and result.status == "unassessed"
    )
    assert result.sample.historical_source_availability == "unknown"
    assert result.sample.context.timestamp == s.context.timestamp
    assert (
        ModelBFinding.model_validate_json(result.model_dump_json()).model_dump_json()
        == result.model_dump_json()
    )


@pytest.mark.parametrize("field", ["feature_order", "units"])
def test_order_and_units(field: str) -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, **{field: tuple(reversed(getattr(s, field)))})


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), True, 1e39]
)
def test_invalid_numeric(value: float) -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, values=(value,) + s.values[1:])


def test_missing_lineage_rejected() -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, feature_evidence_ids=((),) + s.feature_evidence_ids[1:])


@pytest.mark.parametrize(
    "field", ["mission_id", "astronaut_id", "spacecraft_id", "compartment_id"]
)
def test_context_mismatch(field: str) -> None:
    s = sample()
    c = {**s.context.model_dump(), field: "wrong"}
    with pytest.raises((ValidationError, ModelBError)):
        service(s).assess(mutate(s, context=c))


def test_subject_binding_rejects_even_empty_evidence() -> None:
    s = sample()
    other = s.model_copy(
        update={"context": s.context.model_copy(update={"astronaut_id": "wrong"})}
    )
    with pytest.raises((ValidationError, ModelBError)):
        service(s).assess(other)


def test_imputation_preserves_missingness_and_training_values() -> None:
    s = sample(drop_heart=True)
    fake = FakeScorer()
    result = service(s, scorer=fake).assess(s)
    assert result.sample.values[0] is None and fake.rows[0][0] == 1.0
    assert result.imputed_features == ("heart_rate_latest", "heart_rate_mean")
    assert (
        result.imputation_values[0] == result.model.imputation_medians[0]
        if result.model
        else False
    )


def test_all_missing_abstains_without_calling_estimator() -> None:
    s = sample(missing=True)
    fake = FakeScorer()
    result = service(s, scorer=fake).assess(s)
    assert (
        result.status == "abstained" and result.anomaly_score is None and not fake.rows
    )
    assert "no_usable_observed_metrics" in result.reasons


def test_missing_receipt_abstains_without_fallback() -> None:
    s = sample()
    fake = FakeScorer()
    result = service(s, scorer=fake, receipt=False).assess(s)
    assert result.status == "abstained" and not fake.rows
    assert "acquisition_not_verified" in result.reasons


def test_future_acquisition_rejected() -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, acquired_at=s.assessed_at + timedelta(seconds=1))


def test_future_ingestion_abstains() -> None:
    s = sample()
    e = s.evidence[0]
    obs = e.observation.model_copy(
        update={"ingested_at": s.assessed_at + timedelta(seconds=1)}
    )
    e = e.model_copy(update={"observation": obs})
    future = mutate(s, evidence=(e,) + s.evidence[1:])
    assert "future_unavailable_evidence" in service(s).assess(future).reasons


def test_prospective_missing_ingestion_abstains() -> None:
    s = sample()
    evidence = tuple(
        e.model_copy(
            update={
                "observation": e.observation.model_copy(update={"ingested_at": None})
            }
        )
        for e in s.evidence
    )
    live = mutate(s, availability_mode="prospective", evidence=evidence)
    assert "prospective_availability_unknown" in service(s).assess(live).reasons


def test_prospective_valid_availability_permits_score() -> None:
    s = sample()
    result = service(s).assess(mutate(s, availability_mode="prospective"))
    assert result.status == "unassessed" and result.anomaly_score == 0.5


@pytest.mark.parametrize(
    "method,comparison,quantile",
    [
        ("published_estimator_offset", "greater_than", None),
        ("local_training_quantile", "greater_than", 0.99),
        ("exploratory_calibration", "greater_or_equal", None),
    ],
)
@pytest.mark.parametrize("score", [0.49, 0.5, 0.51])
def test_named_policies_at_boundary(
    method: Literal[
        "published_estimator_offset",
        "local_training_quantile",
        "exploratory_calibration",
    ],
    comparison: Literal["greater_than", "greater_or_equal"],
    quantile: float | None,
    score: float,
) -> None:
    policy = ThresholdPolicy(
        model_artifact_sha256=metadata().artifact_sha256,
        derivation_manifest_sha256=DIGEST,
        policy_id="synthetic-policy",
        method=method,
        comparison=comparison,
        quantile=quantile,
        threshold=0.5,
        derivation_reference="synthetic-only",
        approval_reference="synthetic-test-approval",
    )
    s = sample()
    result = service(s, scorer=FakeScorer(-score), policy=policy).assess(s)
    assert result.flagged == (
        score >= 0.5 if comparison == "greater_or_equal" else score > 0.5
    )
    assert result.status == ("flagged" if result.flagged else "not_flagged")


def test_unapproved_policy_remains_unassessed() -> None:
    s = sample()
    policy = ThresholdPolicy(
        model_artifact_sha256=metadata().artifact_sha256,
        derivation_manifest_sha256=DIGEST,
        policy_id="candidate",
        method="published_estimator_offset",
        comparison="greater_than",
        threshold=0.1,
        derivation_reference="candidate",
    )
    result = service(s, policy=policy).assess(s)
    assert result.status == "unassessed" and result.flagged is None


def test_model_unavailable_never_uses_synthetic_fallback() -> None:
    s = sample()
    result = service(s, available=False).assess(s)
    assert (
        result.model is None
        and result.status == "abstained"
        and result.anomaly_score is None
    )


def test_artifact_verification_is_bytes_only() -> None:
    m = metadata()
    raw = m.model_dump_json().encode()
    checked = verify_model_b_artifact(
        metadata_bytes=raw,
        artifact_bytes=b"synthetic-not-a-model",
        expected_metadata_sha256=sha256(raw).hexdigest(),
        expected_artifact_sha256=m.artifact_sha256,
        trusted_local_artifact=True,
        runtime_versions=RUNTIME,
    )
    assert checked.metadata == m


@pytest.mark.parametrize("change", ["trust", "runtime", "metadata_pin", "artifact_pin"])
def test_incompatible_artifact_rejected(change: str) -> None:
    m = metadata()
    raw = m.model_dump_json().encode()
    with pytest.raises(ModelBArtifactError):
        verify_model_b_artifact(
            metadata_bytes=raw,
            artifact_bytes=b"synthetic-not-a-model",
            expected_metadata_sha256="c" * 64
            if change == "metadata_pin"
            else sha256(raw).hexdigest(),
            expected_artifact_sha256="c" * 64
            if change == "artifact_pin"
            else m.artifact_sha256,
            trusted_local_artifact=change != "trust",
            runtime_versions={} if change == "runtime" else RUNTIME,
        )


def test_incompatible_metadata_and_policy() -> None:
    with pytest.raises(ValidationError):
        ModelBMetadata.model_validate(
            {**metadata().model_dump(), "units": ("ppm",) * 16}
        )
    with pytest.raises(ValidationError):
        ThresholdPolicy(
            model_artifact_sha256=metadata().artifact_sha256,
            derivation_manifest_sha256=DIGEST,
            policy_id="wrong",
            method="published_estimator_offset",
            comparison="greater_or_equal",
            threshold=0.5,
            derivation_reference="synthetic",
        )


def test_feature_values_cannot_be_fabricated() -> None:
    s = sample()
    bad = mutate(
        s,
        values=(s.values[0] + 1.0 if s.values[0] is not None else 99.0,) + s.values[1:],
    )
    with pytest.raises(ModelBError):
        service(s).assess(bad)


def test_estimator_invalid_score_is_safe_error() -> None:
    s = sample()
    with pytest.raises(ModelBError, match="estimator scoring failed"):
        service(s, scorer=FakeScorer(float("nan"))).assess(s)


@pytest.mark.parametrize(
    "field,value",
    [("source_origin", "measured"), ("historical_source_availability", "known")],
)
def test_no_real_or_known_historical_fallback(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        mutate(sample(), **{field: value})


def test_unknown_acquisition_abstains_without_manufacturing_time() -> None:
    s = sample()
    unknown = mutate(s, acquired_at=None, acquisition_reference=None)
    result = service(s).assess(unknown)
    assert result.status == "abstained" and result.sample.acquired_at is None
    assert result.sample.historical_source_availability == "unknown"


def test_event_time_is_not_acquisition_proxy() -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, acquired_at=s.context.timestamp - timedelta(seconds=1))


def test_future_event_and_support_rejected() -> None:
    s = sample()
    with pytest.raises(ValidationError):
        mutate(s, assessed_at=s.context.timestamp - timedelta(seconds=1))
    e = s.evidence[0]
    support = e.temporal_support.model_copy(
        update={"end": s.context.timestamp + timedelta(seconds=1)}
    )
    with pytest.raises(ValidationError):
        mutate(
            s,
            evidence=(e.model_copy(update={"temporal_support": support}),)
            + s.evidence[1:],
        )


def test_dataset_and_run_mismatch_rejected() -> None:
    s = sample()
    for field in ("dataset_id", "run_id"):
        with pytest.raises(ValidationError):
            mutate(s, **{field: "wrong"})
    with pytest.raises(ModelBError):
        service(s).assess(mutate(s, dataset_manifest_sha256="f" * 64))


def test_bad_threshold_model_binding_rejected() -> None:
    s = sample()
    policy = ThresholdPolicy(
        policy_id="other-model",
        model_artifact_sha256="c" * 64,
        derivation_manifest_sha256=DIGEST,
        method="published_estimator_offset",
        threshold=0.5,
        comparison="greater_than",
        derivation_reference="synthetic",
    )
    with pytest.raises(ModelBError):
        service(s, policy=policy)


def test_replay_result_cannot_be_relabelled_live() -> None:
    s = sample()
    result = service(s).assess(s)
    with pytest.raises(ValidationError):
        ModelBFinding.model_validate(
            {
                **result.model_dump(),
                "evidence_availability_scope": "declared_source_stream",
            }
        )


def test_imputation_metadata_cannot_be_rewritten() -> None:
    s = sample(drop_heart=True)
    result = service(s).assess(s)
    with pytest.raises(ValidationError):
        ModelBFinding.model_validate(
            {
                **result.model_dump(),
                "imputation_values": (999.0,) + result.imputation_values[1:],
            }
        )


def test_result_cannot_claim_unapproved_decision() -> None:
    s = sample()
    result = service(s).assess(s)
    with pytest.raises(ValidationError):
        ModelBFinding.model_validate(
            {
                **result.model_dump(),
                "flagged": False,
                "status": "not_flagged",
                "reasons": (),
            }
        )


def test_canonical_layer_has_no_other_model_or_transport_dependencies() -> None:
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "app"
    for name in (
        "schemas/model_b.py",
        "ai/model_b_anomaly.py",
        "storage/model_b_store.py",
    ):
        tree = ast.parse((root / name).read_text())
        modules = [
            n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        ]
        assert not any(
            any(
                key in module
                for key in (
                    "investigation",
                    "environmental_anomaly",
                    "hybrid",
                    "temporal_evidence",
                    "fastapi",
                    "isolation_confinement",
                )
            )
            for module in modules
        )
    schema = ast.parse((root / "schemas/model_b.py").read_text())
    assert not any(
        isinstance(n, ast.ImportFrom)
        and n.module
        and n.module.startswith(("app.ai", "app.features", "app.storage", "app.api"))
        for n in ast.walk(schema)
    )
