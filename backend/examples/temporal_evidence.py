"""Executable SYNTHETIC AI-H1 example; arbitrary values, no medical meaning.

From backend: PYTHONPATH=. python examples/temporal_evidence.py
"""

from datetime import UTC, datetime, timedelta

from app.ai.temporal_evidence import analyze_temporal_evidence
from app.schemas.baseline import ResearchEvidence
from app.schemas.temporal import TemporalPolicy

START = datetime(2030, 1, 1, tzinfo=UTC)


def synthetic_evidence(values: list[float]) -> tuple[ResearchEvidence, ...]:
    """Build deterministic synthetic fixtures with factual synthetic availability."""
    result = []
    for index, value in enumerate(values, start=1):
        event = START + timedelta(seconds=60 * index)
        result.append(
            ResearchEvidence.model_validate(
                {
                    "observation": {
                        "schema_version": "1.0.0",
                        "observation_id": f"synthetic-{index}",
                        "timestamp": event,
                        "ingested_at": event,
                        "domain": "physiological",
                        "metric": "heart_rate",
                        "scope": {
                            "kind": "astronaut",
                            "astronaut_id": "synthetic-subject",
                            "mission_id": "synthetic-mission",
                        },
                        "measurement": {
                            "kind": "numeric",
                            "value": value,
                            "unit": "bpm",
                        },
                        "quality": {"status": "valid"},
                        "provenance": {
                            "source_type": "simulator",
                            "source_id": "synthetic-source",
                            "method": "synthetic-fixture",
                            "origin": "simulated",
                            "simulation": {
                                "scenario_id": "synthetic",
                                "run_id": "synthetic-run",
                                "generator_version": "1.0.0",
                                "seed": 0,
                            },
                        },
                    },
                    "dataset_id": "synthetic-dataset",
                    "run_id": "synthetic-run",
                    "sensor_id": "synthetic-sensor",
                    "sensor_epoch": "epoch-1",
                    "data_origin": "synthetic",
                    "temporal_support": {"start": event, "end": event},
                }
            )
        )
    return tuple(result)


def synthetic_policy(count: int = 5) -> TemporalPolicy:
    """Arbitrary software-test bounds; not approved clinical reference values."""
    return TemporalPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "interpretation": "research_only",
            "policy_id": "synthetic-temporal",
            "policy_version": "1.0.0",
            "scope": {
                "kind": "astronaut",
                "astronaut_id": "synthetic-subject",
                "mission_id": "synthetic-mission",
            },
            "source": {
                "requirement_id": "synthetic-source",
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
            },
            "event_window": {
                "start": START,
                "end": START + timedelta(seconds=60 * count),
            },
            "reference_lower": 0.0,
            "reference_upper": 10.0,
            "trend_direction": "higher_is_worsening",
            "minimum_slope_per_second": 0.01,
            "minimum_observations": 3,
            "minimum_run": 2,
            "maximum_gap_seconds": 120.0,
            "convention_reference": "Synthetic software fixture only; no clinical approval",
        }
    )


if __name__ == "__main__":
    policy = synthetic_policy()
    summary = analyze_temporal_evidence(
        synthetic_evidence([5.0, 5.0, 20.0, 5.0, 5.0]),
        policy=policy,
        assessed_at=policy.event_window.end,
    )
    print(summary.model_dump_json(indent=2))
