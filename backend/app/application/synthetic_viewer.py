"""Read boundary for the optional local-only synthetic viewer."""

from typing import Protocol

from app.schemas.synthetic_viewer import SyntheticCatalog, SyntheticPage


class SyntheticReadSource(Protocol):
    def catalog(self) -> SyntheticCatalog: ...
    def page(
        self,
        mission: str,
        limit: int,
        offset: int,
        metric: str | None = None,
        source_id: str | None = None,
    ) -> SyntheticPage: ...
