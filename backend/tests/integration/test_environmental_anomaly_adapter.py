"""Isolated inference orchestration; no training or real artifacts."""

from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.application.environmental_anomaly import (
    EnvironmentalAnomalyInputError,
    EnvironmentalAnomalyService,
)
from app.schemas.environmental_anomaly_context import (
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
)
from tests.environmental_context_fixtures import START, detector, sample

ASSESSMENT = START + timedelta(days=1)


def test_score_equality_provenance_and_determinism() -> None:
    source = sample()
    before = source.model_dump_json()
    service = EnvironmentalAnomalyService(detector())
    result = service.assess([source], assessed_at=ASSESSMENT)[0]
    assert (
        result.status == "flagged" and result.anomaly_score == result.threshold == 0.5
    )
    assert result.model and result.model.model_version == "1.1.0"
    assert result.sample.features[0].observation_ids
    assert result.imputed_features and not result.abstention_reasons
    assert source.model_dump_json() == before
    assert (
        service.assess([source], assessed_at=ASSESSMENT)[0].model_dump_json()
        == result.model_dump_json()
    )
    assert (
        EnvironmentalAnomalyContext.model_validate_json(result.model_dump_json())
        == result
    )


def test_missing_measurement_abstains() -> None:
    result = EnvironmentalAnomalyService(detector()).assess(
        [sample(missing=True)], assessed_at=ASSESSMENT
    )[0]
    assert result.status == "abstained" and result.anomaly_score is None
    assert result.abstention_reasons and result.compatibility == "compatible"


def test_no_threshold_is_unassessed() -> None:
    result = EnvironmentalAnomalyService(detector(threshold=False)).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    assert result.status == "unassessed" and result.threshold is None


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_id",
        "duplicate_time",
        "order",
        "future",
        "naive",
        "synthetic",
        "stream",
    ],
)
def test_invalid_batch(kind: str) -> None:
    first, second = sample(), sample(1)
    samples = [first, second]
    at = ASSESSMENT
    if kind == "duplicate_id":
        second = EnvironmentalSample.model_validate(
            {**second.model_dump(), "sample_id": first.sample_id}
        )
        samples = [first, second]
    elif kind == "duplicate_time":
        samples = [
            first,
            EnvironmentalSample.model_validate(
                {**first.model_dump(), "sample_id": "other"}
            ),
        ]
    elif kind == "order":
        samples.reverse()
    elif kind == "future":
        at = START
    elif kind == "naive":
        at = at.replace(tzinfo=None)
    elif kind == "stream":
        second = EnvironmentalSample.model_validate(
            {
                **second.model_dump(),
                "scope": {**second.scope.model_dump(), "run_id": "other"},
            }
        )
        samples = [first, second]
    else:
        payload = first.model_dump()
        payload["scope"]["data_origin"] = "synthetic"
        for obs in payload["observations"]:
            obs["provenance"] = {
                "source_type": "simulator",
                "source_id": "fixture",
                "origin": "simulated",
                "method": "test",
                "simulation": {
                    "run_id": "test",
                    "scenario_id": "test",
                    "generator_version": "test",
                    "seed": 0,
                },
            }
        samples = [EnvironmentalSample.model_validate(payload)]
    with pytest.raises(EnvironmentalAnomalyInputError):
        EnvironmentalAnomalyService(detector()).assess(samples, assessed_at=at)


def test_missing_artifact_explicit(tmp_path: Path) -> None:
    result = EnvironmentalAnomalyService.from_artifact(tmp_path).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    assert result.status == "abstained" and result.availability == "unavailable"
    assert result.abstention_reasons == ("model_unavailable",)


def test_incompatible_artifact_explicit(tmp_path: Path) -> None:
    (tmp_path / "model.joblib").write_bytes(b"not executable")
    (tmp_path / "metadata.json").write_text("{}")
    result = EnvironmentalAnomalyService.from_artifact(tmp_path).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    assert result.compatibility == "incompatible" and result.anomaly_score is None


def test_incompatible_result_version() -> None:
    with pytest.raises(EnvironmentalAnomalyInputError, match="identity"):
        EnvironmentalAnomalyService(detector("2.0.0")).assess(
            [sample()], assessed_at=ASSESSMENT
        )


@pytest.mark.parametrize("change", ["flag", "score", "reasons", "limitations"])
def test_sidecar_rejects_contradictions(change: str) -> None:
    result = EnvironmentalAnomalyService(detector()).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    payload = result.model_dump()
    if change == "flag":
        payload["status"] = "not_flagged"
    elif change == "score":
        payload["anomaly_score"] = None
    elif change == "reasons":
        payload["abstention_reasons"] = ["contradiction"]
    else:
        payload["limitations"] = []
    with pytest.raises(ValidationError):
        EnvironmentalAnomalyContext.model_validate(payload)


def test_features_must_match_original_observations() -> None:
    payload = sample().model_dump()
    payload["features"][0]["value"] = 999.0
    altered = EnvironmentalSample.model_validate(payload)
    with pytest.raises(EnvironmentalAnomalyInputError, match="transformation"):
        EnvironmentalAnomalyService(detector()).assess(
            [altered], assessed_at=ASSESSMENT
        )


def test_existing_m2_and_m4_outputs_unchanged() -> None:
    from app.ai.hazard_reasoning import investigate
    from simulator.mission_generator import SimulationConfig, generate_mission
    from tests.unit.test_research_contracts import finding, group, profile

    mission = generate_mission(
        SimulationConfig(steps=3, episodes_per_scenario=1, missing_probability=0)
    )
    reference_mission = generate_mission(
        SimulationConfig(
            steps=3,
            episodes_per_scenario=1,
            missing_probability=0,
            start=mission.anchors[0].timestamp - timedelta(hours=1),
        )
    )
    reference = reference_mission.anchors[-1]
    current = mission.anchors[-1]
    investigation = investigate(
        mission.observations, current, reference_mission.observations, reference
    )
    contracts = (investigation, profile(), finding(), group())
    before = tuple(c.model_dump_json() for c in contracts)
    EnvironmentalAnomalyService(detector()).assess([sample()], assessed_at=ASSESSMENT)
    assert tuple(c.model_dump_json() for c in contracts) == before
    assert (
        investigate(
            mission.observations, current, reference_mission.observations, reference
        ).model_dump_json()
        == before[0]
    )


def test_unsupported_artifact_version_never_deserialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    import app.application.environmental_anomaly as application

    (tmp_path / "model.joblib").write_bytes(b"must not be loaded")
    (tmp_path / "metadata.json").write_text("{}")
    monkeypatch.setattr(
        application,
        "read_metadata",
        lambda _: SimpleNamespace(
            model_version="2.0.0", dataset=SimpleNamespace(schema_version="1.0.0")
        ),
    )

    def forbidden(_: Path) -> None:
        raise AssertionError("unsupported artifact must not be deserialized")

    monkeypatch.setattr(application, "load_model_a", forbidden)
    result = application.EnvironmentalAnomalyService.from_artifact(tmp_path).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    assert result.compatibility == "incompatible"


def test_runtime_mismatch_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    import app.application.environmental_anomaly as application
    from app.storage.nasa_environment_model_store import ModelArtifactError

    (tmp_path / "model.joblib").write_bytes(b"not a real model")
    (tmp_path / "metadata.json").write_text("{}")
    monkeypatch.setattr(
        application,
        "read_metadata",
        lambda _: SimpleNamespace(
            model_version="1.1.0", dataset=SimpleNamespace(schema_version="1.0.0")
        ),
    )

    def incompatible(_: Path) -> None:
        raise ModelArtifactError("scikit-learn version differs")

    monkeypatch.setattr(application, "load_model_a", incompatible)
    result = application.EnvironmentalAnomalyService.from_artifact(tmp_path).assess(
        [sample()], assessed_at=ASSESSMENT
    )[0]
    assert result.compatibility == "incompatible" and result.status == "abstained"


def test_utc_assessment_boundary_and_not_flagged() -> None:
    from datetime import timezone

    from app.schemas.nasa_environment_model import ThresholdSpec

    model = detector()
    model._threshold = ThresholdSpec(
        method="training_score_quantile",
        quantile=0.99,
        value=0.6,
        selected_on_split="train",
        rationale="artificial test",
    )
    source = sample()
    assert source.available_at is not None
    result = EnvironmentalAnomalyService(model).assess(
        [source],
        assessed_at=source.available_at.astimezone(timezone(timedelta(hours=2))),
    )[0]
    assert result.status == "not_flagged" and result.assessed_at == source.available_at


def test_empty_batch() -> None:
    assert (
        EnvironmentalAnomalyService(detector()).assess([], assessed_at=ASSESSMENT) == ()
    )
