# IndexRepository implementation using SQLite and the existing db module.

import sqlite3
from pathlib import Path

from . import db as _db


class SqliteIndexRepository:
    """Implements IndexRepository using the existing db module."""

    def search(
        self,
        db_path: Path,
        query_term: str,
        limit: int = 50,
        package_prefix: str | None = None,
        kind: str | None = None,
        unique_classes: bool = False,
    ) -> list:
        if not query_term or not query_term.strip():
            return []
        with _db.connection(db_path) as conn:
            rows = _db.search_fts(
                conn,
                query_term.strip(),
                limit=limit,
                package_prefix=package_prefix,
                kind=kind,
                unique_classes=unique_classes,
            )
        if unique_classes:
            return list(rows)
        return [
            {
                "package": r["package"],
                "class_name": r["class_name"],
                "kind": r["kind"],
                "method_name": r["method_name"],
                "returns": r["returns"],
                "params": r["params"],
                "const_name": r["const_name"],
                "const_value": r["const_value"],
                "file_path": r["file_path"],
            }
            for r in rows
        ]

    def get_class_and_methods(self, db_path: Path, package: str, class_name: str) -> dict | None:
        with _db.connection(db_path) as conn:
            return _db.get_class_and_methods(conn, package.strip(), class_name.strip())

    def get_method(
        self, db_path: Path, package: str, class_name: str, method_name: str
    ) -> dict | None:
        with _db.connection(db_path) as conn:
            return _db.get_method(conn, package.strip(), class_name.strip(), method_name.strip())

    def list_classes(
        self,
        db_path: Path,
        package_prefix: str,
        prefix_match: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        with _db.connection(db_path) as conn:
            return _db.list_classes(
                conn, package_prefix, prefix_match=prefix_match, limit=limit, offset=offset
            )

    def get_stats(self, db_path: Path) -> tuple[int, int, int]:
        with _db.connection(db_path) as conn:
            return _db.get_stats(conn)

    def list_subpackages(self, db_path: Path, package_prefix: str | None = None) -> list[str]:
        with _db.connection(db_path) as conn:
            return _db.list_subpackages(conn, package_prefix)
