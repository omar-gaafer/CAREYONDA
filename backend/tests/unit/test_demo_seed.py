"""Offline synthetic fixture tests; no training or Auth account fabrication."""

from datetime import UTC

import pytest

from app.ai.hazard_reasoning import investigate
from app.features.temporal_features import SampleAnchor
from app.schemas.observation import METRIC_REGISTRY, Observation
from app.storage.demo_seed import SeedTargetRejected, local_repository
from simulator.demo_seed import CASES, PREFIX, generate_seed, identifier


def test_determinism_and_distinct_seed() -> None:
    first = generate_seed(42)
    assert first.digest() == generate_seed(42).digest()
    assert first.digest() != generate_seed(43).digest()
    assert len(first.observations) == 1332


def test_schema_units_utc_and_synthetic_provenance() -> None:
    bundle = generate_seed()
    assert all(
        Observation.model_validate_json(o.model_dump_json()) == o
        for o in bundle.observations
    )
    assert (
        tuple(
            sorted(bundle.observations, key=lambda o: (o.timestamp, o.observation_id))
        )
        == bundle.observations
    )
    for o in bundle.observations:
        assert o.timestamp.tzinfo == UTC
        assert o.ingested_at is not None and o.ingested_at >= o.timestamp
        assert o.provenance.origin == "simulated"
        assert o.provenance.simulation is not None
        assert o.provenance.source_id.startswith(PREFIX)
        if o.measurement.kind == "numeric":
            assert o.measurement.unit == METRIC_REGISTRY[o.metric].canonical_unit
    assert {
        o.measurement.unit
        for o in bundle.observations
        if o.metric == "cabin_co2_partial_pressure" and o.measurement.kind == "numeric"
    } == {"Pa"}


def test_cases_missingness_and_conflict() -> None:
    observations = generate_seed().observations
    assert {
        o.provenance.simulation.scenario_id
        for o in observations
        if o.provenance.simulation
    } == set(CASES)
    assert sum(o.quality.status == "missing" for o in observations) == 104
    assert sum(o.quality.status == "suspect" for o in observations) == 72
    conflicted = [
        o
        for o in observations
        if o.provenance.simulation
        and o.provenance.simulation.scenario_id == "contradictory"
        and o.metric == "heart_rate"
    ]
    assert len(conflicted) == 72
    assert {
        o.measurement.value for o in conflicted if o.measurement.kind == "numeric"
    } == {72.0, 99.0}


def test_mission_identity_isolation_and_no_auth_rows() -> None:
    bundle = generate_seed()
    for o in bundle.observations:
        if o.scope.kind == "astronaut":
            crew = int(o.scope.astronaut_id.rsplit("-", 1)[-1])
            assert o.scope.mission_id == identifier("mission", crew // 3)
    assert all(row["user_id"] is None for row in bundle.tables["astronaut_profiles"])
    assert not set(bundle.tables) & {
        "profiles",
        "user_roles",
        "doctor_profiles",
        "mission_crew_assignments",
        "doctor_astronaut_assignments",
        "inference_results",
        "investigations",
    }


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://remote.invalid/db",
        "host=localhost dbname=careyonda_demo_seed_test",
        "host=/tmp dbname=valuable_database",
    ],
)
def test_remote_and_unapproved_target_rejected_without_io(url: str) -> None:
    with pytest.raises(SeedTargetRejected):
        local_repository(url)


def test_invalid_seed_rejected() -> None:
    with pytest.raises(ValueError):
        generate_seed(-1)


@pytest.mark.parametrize(
    "case", ["elevated_co2", "sleep_deprivation", "missing", "contradictory"]
)
def test_actual_existing_m2_on_compatible_seed_context(case: str) -> None:
    bundle = generate_seed()

    def context(case: str) -> tuple[tuple[Observation, ...], SampleAnchor]:
        obs = tuple(
            o
            for o in bundle.observations
            if o.provenance.source_id == PREFIX + "-simulator-c0"
            and o.provenance.simulation
            and o.provenance.simulation.scenario_id == case
        )
        return obs, SampleAnchor(
            sample_id="synthetic-seed-" + case,
            episode_id="synthetic-seed-" + case,
            mission_id=identifier("mission", 0),
            astronaut_id=identifier("astronaut", 0),
            spacecraft_id=identifier("ship", 0),
            compartment_id="synthetic-cabin",
            timestamp=max(o.timestamp for o in obs),
        )

    reference, reference_anchor = context("baseline")
    current, anchor = context(case)
    result = investigate(current, anchor, reference, reference_anchor)
    assert result == investigate(current, anchor, reference, reference_anchor)
    assert set(result.observation_ids) <= set(o.observation_id for o in current)
    assert result.safety_status == "not_evaluated"
