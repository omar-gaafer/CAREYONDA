"""Authenticated persistence use case, separate from anonymous synthetic research."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.observation import Observation


class AccessDenied(Exception):
    pass


class StorageUnavailable(Exception):
    pass


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    user_id: UUID
    roles: tuple[str, ...]


class IdentityProvider(Protocol):
    def verify(self, token: str) -> UUID: ...


class RecordRepository(Protocol):
    def principal(self, user_id: UUID) -> Principal: ...
    def allowed(
        self, principal: Principal, mission: str, astronaut: str, at: datetime
    ) -> bool: ...
    def observations(self, mission: str, astronaut: str) -> tuple[Observation, ...]: ...
    def save(self, observation: Observation) -> None: ...
    def create_mission(self, mission: str) -> None: ...


class AuthorizedRecords:
    def __init__(
        self, identity: IdentityProvider, repository: RecordRepository
    ) -> None:
        self.identity = identity
        self.repository = repository

    def authenticate(self, token: str) -> Principal:
        return self.repository.principal(self.identity.verify(token))

    def read(
        self, principal: Principal, mission: str, astronaut: str, now: datetime
    ) -> tuple[Observation, ...]:
        if not self.repository.allowed(principal, mission, astronaut, now):
            raise AccessDenied
        return self.repository.observations(mission, astronaut)

    def write(
        self, principal: Principal, observation: Observation, now: datetime
    ) -> None:
        # This first persistence slice deliberately excludes derived records and
        # non-numeric/subsystem scopes; it cannot discard their lineage silently.
        if (
            observation.scope.kind != "astronaut"
            or observation.measurement.kind != "numeric"
            or observation.provenance.origin == "derived"
            or observation.timestamp > now
            or observation.ingested_at is None
            or observation.ingested_at > now
        ):
            raise AccessDenied
        if not self.repository.allowed(
            principal, observation.scope.mission_id, observation.scope.astronaut_id, now
        ):
            raise AccessDenied
        if not self.repository.allowed(
            principal,
            observation.scope.mission_id,
            observation.scope.astronaut_id,
            observation.timestamp,
        ):
            raise AccessDenied
        # An astronaut may enter their own self-report, never impersonate a sensor.
        if "Admin" not in principal.roles and "Doctor" not in principal.roles:
            if observation.provenance.origin != "self_reported":
                raise AccessDenied
        self.repository.save(observation)

    def create_mission(self, principal: Principal, mission: str) -> None:
        if "Admin" not in principal.roles:
            raise AccessDenied
        self.repository.create_mission(mission)
