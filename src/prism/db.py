# SQLite schema and FTS5 index for the Hytale API (classes and methods).

import sqlite3
from contextlib import contextmanager
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Internal use: open a database connection; creates file and directory if missing.
    Prefer db.connection(db_path) as context manager for proper cleanup."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection(db_path: Path):
    """
    Context manager: open a DB connection and close it on exit (including on exception).
    Usage: with db.connection(db_path) as conn: ...
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create normal tables (classes, methods) and the FTS5 virtual table
    for full-text search. Idempotent: drops and recreates tables if they exist.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package TEXT NOT NULL,
            class_name TEXT NOT NULL,
            kind TEXT NOT NULL,
            file_path TEXT NOT NULL,
            UNIQUE(package, class_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            returns TEXT NOT NULL,
            params TEXT NOT NULL,
            is_static INTEGER NOT NULL DEFAULT 0,
            annotation TEXT,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_methods_class_id ON methods(class_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classes_package ON classes(package)")

    # FTS5 table for symbol/text search (package, class, method, etc.)
    conn.execute("DROP TABLE IF EXISTS api_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE api_fts USING fts5(
            package,
            class_name,
            kind,
            method_name,
            returns,
            params,
            tokenize='unicode61'
        )
    """)
    conn.commit()


def clear_tables(conn: sqlite3.Connection) -> None:
    """Empty data tables (classes, methods, api_fts) for reindexing from scratch."""
    conn.execute("DELETE FROM api_fts")
    conn.execute("DELETE FROM methods")
    conn.execute("DELETE FROM classes")
    conn.commit()


def insert_class(conn: sqlite3.Connection, package: str, class_name: str, kind: str, file_path: str) -> int:
    """Insert a class and return its id. If (package, class_name) already exists, returns existing id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO classes (package, class_name, kind, file_path) VALUES (?, ?, ?, ?)",
        (package, class_name, kind, file_path),
    )
    if cur.lastrowid and cur.lastrowid > 0:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM classes WHERE package = ? AND class_name = ?",
        (package, class_name),
    ).fetchone()
    return row["id"] if row else 0


def insert_method(
    conn: sqlite3.Connection,
    class_id: int,
    method: str,
    returns: str,
    params: str,
    is_static: bool,
    annotation: str | None,
) -> None:
    """Insert a method and its row into api_fts for search."""
    conn.execute(
        "INSERT INTO methods (class_id, method, returns, params, is_static, annotation) VALUES (?, ?, ?, ?, ?, ?)",
        (class_id, method, returns, params, 1 if is_static else 0, annotation),
    )


def insert_fts_row(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
    kind: str,
    method_name: str,
    returns: str,
    params: str,
) -> None:
    """Insert a row into the FTS5 table so it is searchable."""
    conn.execute(
        "INSERT INTO api_fts (package, class_name, kind, method_name, returns, params) VALUES (?, ?, ?, ?, ?, ?)",
        (package, class_name, kind, method_name, returns, params),
    )


def get_stats(conn: sqlite3.Connection) -> tuple[int, int]:
    """Return (number of classes, number of methods)."""
    classes = conn.execute("SELECT COUNT(*) AS n FROM classes").fetchone()["n"]
    methods = conn.execute("SELECT COUNT(*) AS n FROM methods").fetchone()["n"]
    return classes, methods


def get_class_and_methods(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
) -> dict | None:
    """
    Return the class (package, class_name, kind, file_path) and all its methods.
    Each method: method, returns, params, is_static, annotation.
    None if the class does not exist.
    """
    row = conn.execute(
        "SELECT id, package, class_name, kind, file_path FROM classes WHERE package = ? AND class_name = ?",
        (package.strip(), class_name.strip()),
    ).fetchone()
    if row is None:
        return None
    class_id = row["id"]
    methods_rows = conn.execute(
        "SELECT method, returns, params, is_static, annotation FROM methods WHERE class_id = ? ORDER BY method",
        (class_id,),
    ).fetchall()
    methods = [
        {
            "method": m["method"],
            "returns": m["returns"],
            "params": m["params"],
            "is_static": bool(m["is_static"]),
            "annotation": m["annotation"],
        }
        for m in methods_rows
    ]
    return {
        "package": row["package"],
        "class_name": row["class_name"],
        "kind": row["kind"],
        "file_path": row["file_path"],
        "methods": methods,
    }


def get_method(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
    method_name: str,
) -> dict | None:
    """
    Return the class and methods of that class whose name matches method_name.
    Exact name match (includes overloads with different params).
    Returns None if the class does not exist. If it exists but no methods match, methods = [].
    """
    row = conn.execute(
        "SELECT id, package, class_name, kind, file_path FROM classes WHERE package = ? AND class_name = ?",
        (package.strip(), class_name.strip()),
    ).fetchone()
    if row is None:
        return None
    class_id = row["id"]
    methods_rows = conn.execute(
        "SELECT method, returns, params, is_static, annotation FROM methods WHERE class_id = ? AND method = ? ORDER BY method, params",
        (class_id, method_name.strip()),
    ).fetchall()
    methods = [
        {
            "method": m["method"],
            "returns": m["returns"],
            "params": m["params"],
            "is_static": bool(m["is_static"]),
            "annotation": m["annotation"],
        }
        for m in methods_rows
    ]
    return {
        "package": row["package"],
        "class_name": row["class_name"],
        "kind": row["kind"],
        "file_path": row["file_path"],
        "methods": methods,
    }


def list_classes(
    conn: sqlite3.Connection,
    package_prefix: str,
    prefix_match: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    List classes by exact package or prefix.
    If prefix_match is True, package_prefix is used as prefix (package = X OR package LIKE X.%).
    If False, only package = package_prefix.
    limit/offset allow pagination (limit default 100, max 500).
    Returns list of dict with package, class_name, kind, file_path.
    """
    p = package_prefix.strip()
    if not p:
        return []
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    if prefix_match:
        pattern = p if p.endswith(".") else f"{p}."
        cur = conn.execute(
            """SELECT package, class_name, kind, file_path FROM classes
               WHERE package = ? OR package LIKE ?
               ORDER BY package, class_name
               LIMIT ? OFFSET ?""",
            (p, f"{pattern}%", limit, offset),
        )
    else:
        cur = conn.execute(
            """SELECT package, class_name, kind, file_path FROM classes
               WHERE package = ? ORDER BY class_name
               LIMIT ? OFFSET ?""",
            (p, limit, offset),
        )
    return [
        {"package": r["package"], "class_name": r["class_name"], "kind": r["kind"], "file_path": r["file_path"]}
        for r in cur.fetchall()
    ]


def search_fts(
    conn: sqlite3.Connection,
    query_term: str,
    limit: int = 50,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
) -> list[sqlite3.Row] | list[dict]:
    """
    Search the FTS5 table api_fts. query_term is passed to MATCH (FTS5 syntax).
    JOIN with classes to include file_path (relative to decompiled directory).
    package_prefix: optional; filter by exact package or prefix (X or X.%).
    kind: optional; filter by type (class, interface, record, enum).
    unique_classes: if True, return one entry per class (package, class_name, kind, file_path, method_count).
    If False, return one row per method (classic behaviour).
    May raise sqlite3.OperationalError if FTS5 syntax is invalid.
    """
    if not query_term or not query_term.strip():
        return []
    term = query_term.strip()
    # For unique_classes we need more rows to group; then we limit by class
    fetch_limit = limit * 20 if unique_classes else limit
    sql = """SELECT api_fts.package, api_fts.class_name, api_fts.kind, api_fts.method_name,
             api_fts.returns, api_fts.params, c.file_path
             FROM api_fts JOIN classes c ON c.package = api_fts.package AND c.class_name = api_fts.class_name
             WHERE api_fts MATCH ?"""
    params: list = [term]
    if package_prefix and package_prefix.strip():
        p = package_prefix.strip()
        pattern = p if p.endswith(".") else f"{p}."
        sql += " AND (c.package = ? OR c.package LIKE ?)"
        params.extend([p, f"{pattern}%"])
    if kind and kind.strip():
        sql += " AND api_fts.kind = ?"
        params.append(kind.strip().lower())
    sql += " LIMIT ?"
    params.append(fetch_limit)
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    if not unique_classes:
        return rows
    # Deduplicate by (package, class_name) and count matching methods
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in rows:
        key = (r["package"], r["class_name"])
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "package": r["package"],
            "class_name": r["class_name"],
            "kind": r["kind"],
            "file_path": r["file_path"],
            "method_count": sum(1 for x in rows if (x["package"], x["class_name"]) == key),
        })
        if len(out) >= limit:
            break
    return out
