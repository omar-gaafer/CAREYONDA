"""Read-only local synthetic database transport contracts; no inference fields."""

from typing import Literal

from app.schemas.observation import Contract, Identifier, Observation


class MissionSummary(Contract):
    mission_id: Identifier
    spacecraft_ids: tuple[Identifier, ...]
    astronaut_ids: tuple[Identifier, ...]
    source_ids: tuple[Identifier, ...]
    association_basis: Literal["observation_scope"] = "observation_scope"


class SyntheticCatalog(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    source: Literal["synthetic_database"] = "synthetic_database"
    database_engine: Literal["Local PostgreSQL"] = "Local PostgreSQL"
    missions: tuple[MissionSummary, ...]
    table_counts: dict[str, int]
    total_seed_rows: int


class SyntheticPage(Contract):
    api_version: Literal["1.0.0"] = "1.0.0"
    source: Literal["synthetic_database"] = "synthetic_database"
    mission_id: Identifier
    items: tuple[Observation, ...]
    total: int
    limit: int
    offset: int
    missing: int
    suspect: int
