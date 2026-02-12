# Port: asset read/write and full-text search.
from pathlib import Path
from typing import Protocol, Any

class AssetsRepository(Protocol):
    """Read/write access to the indexed assets (metadata, FTS)."""

    def insert_asset(
        self,
        db_path: Path,
        path: str,
        extension: str,
        size: int,
        metadata: str | None,
        version: str
    ) -> None: ...

    def search_assets(
        self,
        db_path: Path,
        query_term: str,
        limit: int = 50
    ) -> list[dict]: ...
