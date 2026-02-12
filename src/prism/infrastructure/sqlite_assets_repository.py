# Infrastructure: AssetsRepository implementation using SQLite.
from pathlib import Path
from . import db as _db
from ..ports.assets_repository import AssetsRepository

class SqliteAssetsRepository:
    """Implements AssetsRepository using the existing db module."""

    def insert_asset(
        self,
        db_path: Path,
        path: str,
        extension: str,
        size: int,
        metadata: str | None,
        version: str
    ) -> None:
        with _db.connection(db_path) as conn:
            _db.insert_asset(conn, path, extension, size, metadata, version)
            conn.commit()

    def search_assets(
        self,
        db_path: Path,
        query_term: str,
        limit: int = 50
    ) -> list[dict]:
        with _db.connection(db_path) as conn:
            return _db.search_assets_fts(conn, query_term, limit)
