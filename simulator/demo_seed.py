"""Deterministic synthetic database fixtures; no Auth identities or inference outputs.

The simulator's numerical relationships are toy assumptions, not clinical rules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from pydantic import JsonValue

from app.schemas.observation import METRIC_REGISTRY, Observation
from simulator.mission_generator import SimulationConfig, generate_mission

VERSION = "1.0.0"
PREFIX = "synthetic-demo-v1"
CASES = (
    "baseline",
    "elevated_co2",
    "sleep_deprivation",
    "recent_exercise",
    "missing",
    "contradictory",
)
START = datetime(2026, 1, 1, tzinfo=UTC)
REGISTRY_TABLES = {"metric_definitions", "metric_allowed_scopes", "metric_categories"}
Row = dict[str, JsonValue]


@dataclass(frozen=True)
class SeedBundle:
    seed: int
    observations: tuple[Observation, ...]
    tables: dict[str, list[Row]]

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.tables, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()


def identifier(kind: str, number: int) -> str:
    return f"{PREFIX}-{kind}-{number:02d}"


def generate_seed(seed: int = 42) -> SeedBundle:
    if seed < 0:
        raise ValueError("seed must be nonnegative")
    tables: dict[str, list[Row]] = {
        name: []
        for name in (
            "missions",
            "spacecraft",
            "compartments",
            "astronaut_profiles",
            "observations",
            "numeric_measurements",
            "boolean_measurements",
            "categorical_measurements",
            "unavailable_measurements",
            "observation_quality_reasons",
        )
    }
    for mission_number in range(2):
        tables["missions"].append({"mission_id": identifier("mission", mission_number)})
        ship = identifier("ship", mission_number)
        tables["spacecraft"].append({"spacecraft_id": ship})
        tables["compartments"].append(
            {"spacecraft_id": ship, "compartment_id": "synthetic-cabin"}
        )
    observations = []
    for crew in range(6):
        astronaut = identifier("astronaut", crew)
        mission = identifier("mission", crew // 3)
        ship = identifier("ship", crew // 3)
        tables["astronaut_profiles"].append(
            {"astronaut_id": astronaut, "user_id": None}
        )
        generated = generate_mission(
            SimulationConfig(
                seed=seed + crew,
                episodes_per_scenario=1,
                steps=6,
                start=START,
                missing_probability=0.03,
            )
        )
        for case_index, case in enumerate(CASES):
            source_case = case if case in CASES[:4] else "baseline"
            originals = [
                o
                for o in generated.observations
                if o.provenance.simulation is not None
                and o.provenance.simulation.scenario_id == source_case
            ]
            for index, o in enumerate(originals):
                data = o.model_dump(mode="json")
                scope = dict(data["scope"])
                scope["mission_id"] = mission
                if scope["kind"] == "astronaut":
                    scope["astronaut_id"] = astronaut
                else:
                    scope["spacecraft_id"] = ship
                data["scope"] = scope
                stamp = o.timestamp + timedelta(days=case_index)
                data["timestamp"] = stamp.isoformat()
                assert o.ingested_at is not None
                data["ingested_at"] = (
                    o.ingested_at + timedelta(days=case_index)
                ).isoformat()
                oid = f"{PREFIX}-{seed}-c{crew}-{case}-{index:03d}"
                data["observation_id"] = oid
                provenance = dict(data["provenance"])
                provenance["source_id"] = f"{PREFIX}-simulator-c{crew}"
                provenance["method"] = "synthetic_demo_fixture"
                provenance["simulation"] = {
                    "scenario_id": case,
                    "run_id": f"{PREFIX}-seed-{seed}",
                    "generator_version": VERSION,
                    "seed": seed,
                }
                data["provenance"] = provenance
                if case == "missing" and o.metric in {"heart_rate", "sleep_duration"}:
                    data["measurement"] = {
                        "kind": "unavailable",
                        "reason": "not_received",
                    }
                    data["quality"] = {
                        "status": "missing",
                        "reason_codes": ["synthetic_dropout"],
                    }
                if case == "sleep_deprivation" and o.metric == "fatigue_self_report":
                    data["measurement"] = {"kind": "categorical", "value": "very_tired"}
                    data["quality"] = {"status": "valid"}
                if case == "contradictory" and o.metric == "heart_rate":
                    # Deliberately inconsistent simultaneous simulator reports;
                    # neither value is declared medically normal or pathological.
                    data["measurement"] = {
                        "kind": "numeric",
                        "value": 72.0,
                        "unit": "bpm",
                    }
                    data["quality"] = {
                        "status": "suspect",
                        "reason_codes": ["synthetic_conflict"],
                    }
                    other = {
                        **data,
                        "observation_id": oid + "-conflict",
                        "measurement": {
                            "kind": "numeric",
                            "value": 99.0,
                            "unit": "bpm",
                        },
                    }
                    observations.append(Observation.model_validate(other))
                observations.append(Observation.model_validate(data))
    observations.sort(key=lambda o: (o.timestamp, o.observation_id))
    for o in observations:
        rid = str(uuid5(NAMESPACE_URL, "careyonda-demo:" + o.observation_id))
        sim = o.provenance.simulation
        assert sim is not None and o.ingested_at is not None
        observation_scope = o.scope
        row: Row = {
            "record_id": rid,
            "observation_id": o.observation_id,
            "schema_version": o.schema_version,
            "event_at": o.timestamp.isoformat(),
            "ingested_at": o.ingested_at.isoformat(),
            "domain": o.domain,
            "metric_id": o.metric,
            "metric_kind": METRIC_REGISTRY[o.metric].measurement_kind,
            "measurement_kind": o.measurement.kind,
            "scope_kind": observation_scope.kind,
            "mission_id": observation_scope.mission_id,
            "astronaut_id": observation_scope.astronaut_id
            if observation_scope.kind == "astronaut"
            else None,
            "spacecraft_id": observation_scope.spacecraft_id
            if observation_scope.kind in ("spacecraft", "compartment")
            else None,
            "compartment_id": observation_scope.compartment_id
            if observation_scope.kind == "compartment"
            else None,
            "quality_status": o.quality.status,
            "sensor_confidence": o.quality.sensor_confidence,
            "source_type": o.provenance.source_type,
            "source_id": o.provenance.source_id,
            "method": o.provenance.method,
            "origin": o.provenance.origin,
            "simulation_scenario_id": sim.scenario_id,
            "simulation_run_id": sim.run_id,
            "simulation_generator_version": sim.generator_version,
            "simulation_seed": sim.seed,
        }
        tables["observations"].append(row)
        measurement: Row = {"record_id": rid, "metric_id": o.metric}
        if o.measurement.kind == "unavailable":
            measurement.update(
                metric_kind=METRIC_REGISTRY[o.metric].measurement_kind,
                reason=o.measurement.reason,
            )
            table = "unavailable_measurements"
        else:
            measurement["value"] = o.measurement.value
            if o.measurement.kind == "numeric":
                measurement["unit"] = o.measurement.unit
            table = o.measurement.kind + "_measurements"
        tables[table].append(measurement)
        for reason in o.quality.reason_codes:
            tables["observation_quality_reasons"].append(
                {"record_id": rid, "reason_code": reason}
            )
    return SeedBundle(seed, tuple(observations), tables)
