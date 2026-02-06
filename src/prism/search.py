# Search access layer: resolves root/version, opens DB and runs FTS5.
# Unifies logic used by CLI and MCP to avoid duplication and ease future changes.

import sqlite3
from pathlib import Path

from . import config
from . import db
from . import i18n


def search_api(
    root: Path | None = None,
    version: str = "release",
    query: str = "",
    limit: int = 50,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
) -> tuple[list[dict], dict | None]:
    """
    Run FTS5 search on the DB for the given version.
    Resolves project root and DB path; opens/closes connection with context manager.
    package_prefix and kind are optional filters. unique_classes: if True, one entry per class (with method_count).

    Returns:
        (result list, None) on success. If unique_classes=False: package, class_name, kind, method_name, returns, params, file_path.
        If unique_classes=True: package, class_name, kind, file_path, method_count.
        ([], error dict) on failure.
    """
    root = root or config.get_project_root()
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    term = query.strip() if query else ""
    limit = max(1, min(limit, 500))

    db_path = config.get_db_path(root, version)
    if not db_path.is_file():
        return ([], {
            "error": "no_db",
            "message": i18n.t("cli.query.no_db", version=version),
        })

    try:
        with db.connection(db_path) as conn:
            rows = db.search_fts(
                conn, term, limit=limit, package_prefix=package_prefix, kind=kind, unique_classes=unique_classes
            )
        if unique_classes:
            # search_fts already returns list[dict] with package, class_name, kind, file_path, method_count
            results = list(rows)
        else:
            results = [
                {
                    "package": r["package"],
                    "class_name": r["class_name"],
                    "kind": r["kind"],
                    "method_name": r["method_name"],
                    "returns": r["returns"],
                    "params": r["params"],
                    "file_path": r["file_path"],
                }
                for r in rows
            ]
        return (results, None)
    except sqlite3.OperationalError as e:
        err_msg = str(e).lower()
        if "fts5" in err_msg or "syntax" in err_msg:
            return ([], {
                "error": "fts5_syntax",
                "message": str(e),
                "hint": i18n.t("cli.query.fts5_help"),
            })
        return ([], {"error": "db", "message": str(e)})
    except Exception as e:
        return ([], {"error": "db", "message": str(e)})
