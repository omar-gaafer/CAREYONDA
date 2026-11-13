"""Artificial observations exercising real-source declarations; no NASA values."""

from datetime import UTC, datetime, timedelta

import numpy as np

from app.ai.nasa_environment_anomaly import (
    FloatMatrix,
    FloatVector,
    ModelProvenance,
    NasaEnvironmentAnomalyDetector,
    feature_names,
)
from app.features.environmental import build_environment_features, environmental_schema
from app.schemas.environmental_anomaly_context import EnvironmentalSample
from app.schemas.nasa_environment_model import PreprocessingSpec, ThresholdSpec
from app.schemas.observation import Observation

START = datetime(2030, 1, 1, tzinfo=UTC)


def sample(index: int = 0, *, missing: bool = False) -> EnvironmentalSample:
    time = START + timedelta(minutes=index * 5)
    observations = []
    for metric, unit, value in [
        ("cabin_co2_concentration", "ppm", 100.0),
        ("environment_temperature", "degC", 10.0),
        ("relative_humidity", "%", 20.0),
    ]:
        absent = missing and metric == "cabin_co2_concentration"
        observations.append(
            Observation.model_validate(
                {
                    "schema_version": "1.0.0",
                    "observation_id": f"artificial-{index}-{metric}",
                    "timestamp": time,
                    "ingested_at": time + timedelta(seconds=1),
                    "domain": "environmental",
                    "metric": metric,
                    "scope": {
                        "kind": "spacecraft",
                        "spacecraft_id": "ISS",
                        "mission_id": "NASA-RR1",
                    },
                    "measurement": {"kind": "unavailable", "reason": "not_received"}
                    if absent
                    else {"kind": "numeric", "value": value, "unit": unit},
                    "quality": {
                        "status": "missing",
                        "reason_codes": ["fixture_missing"],
                    }
                    if absent
                    else {"status": "valid"},
                    "provenance": {
                        "source_type": "mission_log",
                        "source_id": "artificial-environment",
                        "origin": "measured",
                        "method": "artificial-test",
                    },
                }
            )
        )
    built = build_environment_features(observations)[0]
    schema = environmental_schema()["features"]
    assert isinstance(schema, list)
    return EnvironmentalSample.model_validate(
        {
            "sample_id": built.sample_id,
            "scope": {
                "mission_id": "NASA-RR1",
                "spacecraft_id": "ISS",
                "data_origin": "real",
                "dataset_id": "artificial",
                "run_id": "test",
            },
            "event_time_utc": time,
            "available_at": time + timedelta(seconds=1),
            "transformation_version": "environmental-1.0.0",
            "features": [
                {
                    "name": f["name"],
                    "unit": f["unit"],
                    "value": built.values[f["name"]],
                    "observation_ids": built.evidence[f["name"]],
                }
                for f in schema
            ],
            "observations": observations,
        }
    )


class FixedEstimator:
    def score_samples(self, X: FloatMatrix) -> FloatVector:
        return np.full(len(X), -0.5, dtype=np.float64)


def detector(
    version: str = "1.1.0", *, threshold: bool = True
) -> NasaEnvironmentAnomalyDetector:
    names = feature_names()
    return NasaEnvironmentAnomalyDetector(
        FixedEstimator(),
        PreprocessingSpec(
            feature_names=names,
            impute_median={
                n: 0.0 for n in names if n.endswith("_delta") or n == "gap_seconds"
            },
            abstain_if_missing=tuple(
                n for n in names if n.endswith(("_value", "_mean_30m"))
            ),
            training_constants={},
            method="artificial-test",
        ),
        ThresholdSpec(
            method="training_score_quantile",
            quantile=0.99,
            value=0.5,
            selected_on_split="train",
            rationale="artificial equality test",
        )
        if threshold
        else None,
        ModelProvenance(
            "careyonda-model-a-nasa-rr1-environment-iforest",
            version,
            "0" * 64,
            "1.0.0",
            "1" * 64,
            "training_score_quantile" if threshold else None,
        ),
    )
