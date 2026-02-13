# SQLite schema and FTS5 index for the Hytale API (classes and methods).

import sqlite3
from contextlib import contextmanager
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Internal use: opens connection to the database; creates file and directory if they don't exist.
    Prefer db.connection(db_path) as a context manager for proper closing."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection(db_path: Path):
    """
    Context manager: opens connection and closes it on exit (including on exceptions).
    Usage: with db.connection(db_path) as conn: ...
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Creates normal tables (classes, methods) and the FTS5 virtual table for searching.
    Drops and recreates tables to ensure schema synchronization.
    """
    conn.execute("DROP TABLE IF EXISTS api_fts")
    conn.execute("DROP TABLE IF EXISTS methods")
    conn.execute("DROP TABLE IF EXISTS constants")
    conn.execute("DROP TABLE IF EXISTS classes")
    
    conn.execute("""
        CREATE TABLE classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package TEXT NOT NULL,
            class_name TEXT NOT NULL,
            kind TEXT NOT NULL,
            file_path TEXT NOT NULL,
            parent TEXT,
            interfaces TEXT,
            UNIQUE(package, class_name)
        )
    """)
    conn.execute("""
        CREATE TABLE methods (
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
    conn.execute("""
        CREATE TABLE constants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    conn.execute("CREATE INDEX idx_methods_class_id ON methods(class_id)")
    conn.execute("CREATE INDEX idx_constants_class_id ON constants(class_id)")
    conn.execute("CREATE INDEX idx_classes_package ON classes(package)")

    conn.execute("""
        CREATE VIRTUAL TABLE api_fts USING fts5(
            package,
            class_name,
            kind,
            method_name,
            returns,
            params,
            const_name,
            const_value,
            snippet,
            tokenize='unicode61'
        )
    """)
    conn.commit()


def init_assets_schema(conn: sqlite3.Connection) -> None:
    """
    Creates tables for assets (metadata and FTS).
    """
    conn.execute("DROP TABLE IF EXISTS assets_fts")
    conn.execute("DROP TABLE IF EXISTS assets")
    
    conn.execute("""
        CREATE TABLE assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            extension TEXT NOT NULL,
            size INTEGER NOT NULL,
            category TEXT,
            internal_id TEXT,
            width INTEGER,
            height INTEGER,
            metadata TEXT,
            version TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE VIRTUAL TABLE assets_fts USING fts5(
            path,
            category,
            internal_id,
            metadata,
            tokenize='trigram'
        )
    """)
    conn.commit()


def clear_tables(conn: sqlite3.Connection) -> None:
    """Empties data tables (classes, methods, constants, api_fts) to reindex from scratch."""
    conn.execute("DELETE FROM api_fts")
    conn.execute("DELETE FROM methods")
    conn.execute("DELETE FROM constants")
    conn.execute("DELETE FROM classes")
    conn.commit()


def insert_class(conn: sqlite3.Connection, package: str, class_name: str, kind: str, file_path: str, parent: str | None = None, interfaces: str | None = None) -> int:
    """Inserts a class and returns its id. If (package, class_name) exists, returns the existing id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO classes (package, class_name, kind, file_path, parent, interfaces) VALUES (?, ?, ?, ?, ?, ?)",
        (package, class_name, kind, file_path, parent, interfaces),
    )
    if cur.lastrowid and cur.lastrowid > 0:
        return cur.lastrowid

    # If already exists, we might need to update parent/interfaces if they were NULL before
    # (e.g. if we indexed a reference before the actual definition)
    conn.execute(
        "UPDATE classes SET parent = ?, interfaces = ?, kind = ?, file_path = ? WHERE package = ? AND class_name = ?",
        (parent, interfaces, kind, file_path, package, class_name)
    )
    
    row = conn.execute(
        "SELECT id FROM classes WHERE package = ? AND class_name = ?",
        (package, class_name),
    ).fetchone()
    return row["id"] if row else 0


def insert_constant(
    conn: sqlite3.Connection,
    class_id: int,
    name: str,
    type_name: str,
    value: str,
) -> None:
    """Inserts a constant."""
    conn.execute(
        "INSERT INTO constants (class_id, name, type, value) VALUES (?, ?, ?, ?)",
        (class_id, name, type_name, value),
    )


def insert_method(
    conn: sqlite3.Connection,
    class_id: int,
    method: str,
    returns: str,
    params: str,
    is_static: bool,
    annotation: str | None,
) -> None:
    """Inserts a method."""
    conn.execute(
        "INSERT INTO methods (class_id, method, returns, params, is_static, annotation) VALUES (?, ?, ?, ?, ?, ?)",
        (class_id, method, returns, params, 1 if is_static else 0, annotation),
    )


def insert_fts_row(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
    kind: str,
    method_name: str | None = None,
    returns: str | None = None,
    params: str | None = None,
    const_name: str | None = None,
    const_value: str | None = None,
    snippet: str | None = None,
) -> None:
    """Inserts a row into the FTS5 table to make it searchable."""
    conn.execute(
        "INSERT INTO api_fts (package, class_name, kind, method_name, returns, params, const_name, const_value, snippet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (package, class_name, kind, method_name, returns, params, const_name, const_value, snippet),
    )


def get_stats(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """Returns (number of classes, number of methods, number of constants)."""
    classes = conn.execute("SELECT COUNT(*) AS n FROM classes").fetchone()["n"]
    methods = conn.execute("SELECT COUNT(*) AS n FROM methods").fetchone()["n"]
    constants = conn.execute("SELECT COUNT(*) AS n FROM constants").fetchone()["n"]
    return classes, methods, constants


def get_class_and_methods(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
) -> dict | None:
    """Returns the class and all its methods. None if not found."""
    row = conn.execute(
        "SELECT id, package, class_name, kind, file_path, parent, interfaces FROM classes WHERE package = ? AND class_name = ?",
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
    const_rows = conn.execute(
        "SELECT name, type, value FROM constants WHERE class_id = ? ORDER BY name",
        (class_id,),
    ).fetchall()
    constants = [
        {"name": c["name"], "type": c["type"], "value": c["value"]}
        for c in const_rows
    ]
    return {
        "package": row["package"],
        "class_name": row["class_name"],
        "kind": row["kind"],
        "file_path": row["file_path"],
        "parent": row["parent"],
        "interfaces": row["interfaces"],
        "methods": methods,
        "constants": constants,
    }


def get_method(
    conn: sqlite3.Connection,
    package: str,
    class_name: str,
    method_name: str,
) -> dict | None:
    """Returns the class and methods that match method_name. None if the class doesn't exist."""
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
    """Lists classes by exact package or prefix. limit/offset for pagination."""
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


def list_subpackages(conn: sqlite3.Connection, package_prefix: str | None = None) -> list[str]:
    """
    Lists unique subpackages for a given prefix.
    If prefix is 'com.hypixel', it might return ['com.hypixel.hytale', 'com.hypixel.fastutil'].
    """
    if not package_prefix:
        cur = conn.execute("SELECT DISTINCT package FROM classes ORDER BY package")
    else:
        p = package_prefix.strip()
        pattern = p if p.endswith(".") else f"{p}."
        cur = conn.execute(
            "SELECT DISTINCT package FROM classes WHERE package LIKE ? ORDER BY package",
            (f"{pattern}%",),
        )
    
    packages = [r["package"] for r in cur.fetchall()]
    
    #_ If we want only the immediate next level, we could process it here.
    #_ For now, returning all subpackages that match the prefix is very useful.
    return packages


def search_fts(
    conn: sqlite3.Connection,
    query_term: str,
    limit: int = 50,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
) -> list[sqlite3.Row] | list[dict]:
    """Searches in the FTS5 table api_fts. unique_classes: one entry per class with method_count."""
    if not query_term or not query_term.strip():
        return []
    from . import search_utils
    term = search_utils.sanitize_fts_query(query_term)
    
    fetch_limit = limit * 20 if unique_classes else limit
    sql = """SELECT api_fts.package, api_fts.class_name, api_fts.kind, api_fts.method_name,
             api_fts.returns, api_fts.params, api_fts.const_name, api_fts.const_value,
             api_fts.snippet, c.file_path,
             api_fts.rank
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
    sql += " ORDER BY api_fts.rank"
    sql += " LIMIT ?"
    params.append(fetch_limit)
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    if not unique_classes:
        return rows
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


def find_implementations(conn: sqlite3.Connection, target_name: str, limit: int = 100) -> list[dict]:
    """
    Finds classes that implement an interface or extend a class.
    Searches in 'parent' and 'interfaces' columns.
    """
    term = f"%{target_name}%"
    cur = conn.execute(
        """SELECT package, class_name, kind, parent, interfaces, file_path 
           FROM classes 
           WHERE parent LIKE ? OR interfaces LIKE ?
           ORDER BY package, class_name
           LIMIT ?""",
        (term, term, limit),
    )
    return [
        {
            "package": r["package"],
            "class_name": r["class_name"],
            "kind": r["kind"],
            "parent": r["parent"],
            "interfaces": r["interfaces"],
            "file_path": r["file_path"],
        }
        for r in cur.fetchall()
    ]


def list_events(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    """
    Lists Hytale events.
    1. Classes ending with 'Event'.
    2. Methods annotated with '@Subscribe' (or similar event annotations).
    """
    #_ Find classes that look like events
    cur = conn.execute(
        """SELECT package, class_name, kind, file_path 
           FROM classes 
           WHERE class_name LIKE '%Event'
           ORDER BY package, class_name
           LIMIT ?""",
        (limit,),
    )
    event_classes = [dict(r) for r in cur.fetchall()]
    
    #_ Find methods that handle events (annotated with @Subscribe)
    #_ We reuse the limit or use a fraction of it
    cur = conn.execute(
        """SELECT c.package, c.class_name, m.method, m.params, m.annotation
           FROM methods m
           JOIN classes c ON c.id = m.class_id
           WHERE m.annotation LIKE '%Subscribe%'
           LIMIT ?""",
        (limit,),
    )
    subscriptions = [dict(r) for r in cur.fetchall()]
    
    return {
        "event_classes": event_classes,
        "subscriptions": subscriptions
    }
def find_systems_for_component(conn: sqlite3.Connection, component_name: str, limit: int = 100) -> list[dict]:
    """
    Finds systems that process a specific component.
    Searches for classes with 'System' in the name having methods with the component in their parameters.
    """
    cur = conn.execute(
        """SELECT DISTINCT c.package, c.class_name, c.file_path, m.method, m.params
           FROM classes c
           JOIN methods m ON c.id = m.class_id
           WHERE c.class_name LIKE '%System%'
             AND m.params LIKE ?
           ORDER BY c.package, c.class_name
           LIMIT ?""",
        (f"%{component_name}%", limit),
    )
    return [dict(r) for r in cur.fetchall()]


def insert_asset(
    conn: sqlite3.Connection,
    path: str,
    extension: str,
    size: int,
    category: str | None,
    internal_id: str | None,
    width: int | None,
    height: int | None,
    metadata: str | None,
    version: str
) -> None:
    """Inserts an asset into assets and assets_fts tables."""
    conn.execute(
        """INSERT OR REPLACE INTO assets 
           (path, extension, size, category, internal_id, width, height, metadata, version) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (path, extension, size, category, internal_id, width, height, metadata, version)
    )
    conn.execute(
        "INSERT INTO assets_fts (path, category, internal_id, metadata) VALUES (?, ?, ?, ?)",
        (path, category, internal_id, metadata)
    )


def search_assets_fts(conn: sqlite3.Connection, query_term: str, limit: int = 50) -> list[dict]:
    """Searches assets using FTS5."""
    if not query_term or not query_term.strip():
        return []
    
    from . import search_utils
    term = search_utils.sanitize_fts_query(query_term)
    
    cur = conn.execute(
        """SELECT a.path, a.extension, a.size, a.category, a.internal_id, a.width, a.height, a.metadata, a.version
           FROM assets a
           JOIN assets_fts f ON a.path = f.path
           WHERE assets_fts MATCH ?
           ORDER BY f.rank
           LIMIT ?""",
        (term, limit)
    )
    return [dict(r) for r in cur.fetchall()]
