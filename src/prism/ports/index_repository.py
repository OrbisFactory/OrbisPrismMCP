# Port: index read/write and full-text search.

from pathlib import Path
from typing import Any, Protocol


class IndexRepository(Protocol):
    """Read/write access to the indexed API (classes, methods, FTS)."""

    def search(
        self,
        db_path: Path,
        query_term: str,
        limit: int = 50,
        package_prefix: str | None = None,
        kind: str | None = None,
        unique_classes: bool = False,
    ) -> list[dict] | list[Any]: ...
    def get_class_and_methods(self, db_path: Path, package: str, class_name: str) -> dict | None: ...
    def get_method(self, db_path: Path, package: str, class_name: str, method_name: str) -> dict | None: ...
    def list_classes(
        self,
        db_path: Path,
        package_prefix: str,
        prefix_match: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]: ...
    def get_stats(self, db_path: Path) -> tuple[int, int, int]: ...
