# Use case: FTS search on the index.

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider, IndexRepository


def search_api(
    config_provider: "ConfigProvider",
    index_repository: "IndexRepository",
    root: Path | None,
    version: str,
    query: str,
    limit: int = 50,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
    t: callable = None,
) -> tuple[list[dict], dict | None]:
    """
    Run FTS5 search. Returns (results, None) on success or ([], error_dict) on failure.
    t: optional i18n translate function for error messages.
    """
    from ..domain.constants import normalize_version

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    term = (query or "").strip()
    limit = max(1, min(limit, 500))
    db_path = config_provider.get_db_path(root, version)
    if not db_path.is_file():
        msg = f"Database for version {version} does not exist. Run prism index first."
        if t:
            msg = t("cli.query.no_db", version=version)
        return ([], {"error": "no_db", "message": msg})
    try:
        results = index_repository.search(
            db_path, term, limit=limit, package_prefix=package_prefix, kind=kind, unique_classes=unique_classes
        )
        return (list(results), None)
    except sqlite3.OperationalError as e:
        err_msg = str(e).lower()
        if "fts5" in err_msg or "syntax" in err_msg:
            hint = t("cli.query.fts5_help") if t else "Use a single word or quoted phrase. Multiple terms: term1 AND term2."
            return ([], {"error": "fts5_syntax", "message": str(e), "hint": hint})
        return ([], {"error": "db", "message": str(e)})
    except Exception as e:
        return ([], {"error": "db", "message": str(e)})
