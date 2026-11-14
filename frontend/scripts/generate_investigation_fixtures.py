"""Generate synthetic frontend fixtures with unchanged local M2 code. Run from root."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.ai.hazard_reasoning import investigate
from app.features.temporal_features import SampleAnchor
from app.schemas.observation import Observation


def generate() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for _number, (name, person) in enumerate(
        [
            ("ranked", "crew-01"),
            ("missing", "crew-02"),
            ("ambiguous", "crew-03"),
            ("conflicting", "crew-01"),
        ]
    ):
        now = datetime(2026, 11, 13, 11, 55, tzinfo=UTC)

        def anchor(
            label: str, time: datetime, name: str = name, person: str = person
        ) -> SampleAnchor:
            return SampleAnchor(
                sample_id=f"{name}-{label}",
                episode_id=f"{name}-episode",
                mission_id="ARES-07",
                astronaut_id=person,
                spacecraft_id="HABITAT-01",
                compartment_id="LAB-01",
                timestamp=time,
            )

        current = anchor("current", now)
        reference = anchor("reference", now - timedelta(minutes=15))

        def observations(
            window: str, endpoint: datetime, name: str = name, person: str = person
        ) -> list[Observation]:
            rows = []
            for step in range(3):
                for metric, value, unit, domain in [
                    (
                        "heart_rate",
                        90.0 if window == "current" else 72.0,
                        "bpm",
                        "physiological",
                    ),
                    (
                        "cabin_co2_partial_pressure",
                        170.0 if window == "current" else 50.0,
                        "Pa",
                        "environmental",
                    ),
                    ("sleep_duration", 8.0, "h", "behavioral"),
                    ("fatigue_self_report", "rested", "1", "behavioral"),
                    (
                        "exercise_active",
                        window == "current" and name == "ambiguous",
                        "1",
                        "mission_context",
                    ),
                    ("communication_delay", 2.0, "s", "mission_context"),
                ]:
                    measurement = (
                        {"kind": "boolean", "value": value}
                        if isinstance(value, bool)
                        else {"kind": "categorical", "value": value}
                        if isinstance(value, str)
                        else {"kind": "numeric", "value": value, "unit": unit}
                    )
                    missing = (
                        name == "missing"
                        and window == "current"
                        and metric == "cabin_co2_partial_pressure"
                    )
                    if missing:
                        measurement = {"kind": "unavailable", "reason": "not_received"}
                    scope = (
                        {
                            "kind": "astronaut",
                            "astronaut_id": person,
                            "mission_id": "ARES-07",
                        }
                        if metric
                        in (
                            "heart_rate",
                            "sleep_duration",
                            "fatigue_self_report",
                            "exercise_active",
                        )
                        else {
                            "kind": "spacecraft",
                            "spacecraft_id": "HABITAT-01",
                            "mission_id": "ARES-07",
                        }
                    )
                    if metric == "cabin_co2_partial_pressure":
                        scope = {
                            "kind": "compartment",
                            "spacecraft_id": "HABITAT-01",
                            "compartment_id": "LAB-01",
                            "mission_id": "ARES-07",
                        }
                    time = endpoint - timedelta(minutes=2 - step)
                    rows.append(
                        Observation.model_validate(
                            dict(
                                schema_version="1.0.0",
                                observation_id=f"{name}-{window}-{metric}-{step}",
                                timestamp=time,
                                ingested_at=time + timedelta(seconds=12),
                                domain=domain,
                                metric=metric,
                                scope=scope,
                                measurement=measurement,
                                quality={
                                    "status": "missing" if missing else "valid",
                                    "reason_codes": ["synthetic_dropout"]
                                    if missing
                                    else [],
                                },
                                provenance={
                                    "source_type": "simulator",
                                    "source_id": "phase2-fixture",
                                    "method": "controlled-synthetic-case",
                                    "origin": "simulated",
                                    "simulation": {
                                        "scenario_id": name,
                                        "run_id": "phase2-v1",
                                        "generator_version": "1.0.0",
                                        "seed": 42,
                                    },
                                },
                            )
                        )
                    )
            return rows

        observed, prior = (
            observations("current", now),
            observations("reference", reference.timestamp),
        )
        if name == "conflicting":
            original = next(o for o in observed if o.metric == "heart_rate")
            observed.append(
                Observation.model_validate(
                    {
                        **original.model_dump(),
                        "observation_id": "conflicting-extra-hr",
                        "measurement": {
                            "kind": "numeric",
                            "value": 110.0,
                            "unit": "bpm",
                        },
                    }
                )
            )
        result = investigate(observed, current, prior, reference)
        expected_status = {
            "ranked": "ranked",
            "missing": "insufficient_evidence",
            "ambiguous": "ambiguous",
            "conflicting": "conflicting_evidence",
        }[name]
        assert result.status == expected_status, (name, result.status)
        cases.append(
            {
                "fixture_version": "1.0.0",
                "origin": "synthetic_precomputed",
                "title": {
                    "ranked": "CO₂ and heart-rate pattern",
                    "missing": "Incomplete cabin evidence",
                    "ambiguous": "Competing synthetic patterns",
                    "conflicting": "Simultaneous conflicting readings",
                }[name],
                "context": current.model_dump(mode="json"),
                "reference_context": reference.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
                "observations": [
                    o.model_dump(mode="json") for o in (*observed, *prior)
                ],
            }
        )
    return cases


if __name__ == "__main__":
    output = Path("frontend/src/infrastructure/fixtures/investigations.json")
    output.write_text(json.dumps(generate(), indent=2) + "\n")
