# src/prism/infrastructure/sqlite_assets_repository.py
from pathlib import Path
from typing import List, Optional
from . import db as _db
from ..ports.assets_repository import AssetsRepository
from ..domain.asset import Asset

class SqliteAssetsRepository:
    """Implements AssetsRepository using the existing db module."""

    def search_assets(self, db_path: Path, query: str, limit: int = 50) -> List[Asset]:
        """Search assets via FTS5."""
        with _db.connection(db_path) as conn:
            rows = _db.search_assets_fts(conn, query, limit)
            return [
                Asset(
                    path=r["path"],
                    extension=r["extension"],
                    size=r["size"],
                    category=r["category"],
                    internal_id=r["internal_id"],
                    width=r["width"],
                    height=r["height"],
                    metadata=r["metadata"],
                    version=r["version"]
                )
                for r in rows
            ]

    def get_asset_by_path(self, db_path: Path, path: str) -> Optional[Asset]:
        """Get a specific asset by its path."""
        with _db.connection(db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM assets WHERE path = ?",
                (path,)
            )
            r = cur.fetchone()
            if not r:
                return None
            return Asset(
                path=r["path"],
                extension=r["extension"],
                size=r["size"],
                category=r["category"],
                internal_id=r["internal_id"],
                width=r["width"],
                height=r["height"],
                metadata=r["metadata"],
                version=r["version"]
            )
