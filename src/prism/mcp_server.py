# MCP server for Orbis Prism (official SDK: https://github.com/modelcontextprotocol/python-sdk).
# Exposes prism_* tools to search the indexed Hytale API.
# Compatible with mcp>=1.0 (v1.x uses FastMCP; v2 uses MCPServer).
# Transport: stdio (default) or streamable-http (useful for Docker).

import json

from mcp.server.fastmcp import FastMCP

from . import config
from . import db
from . import i18n
from . import search


def _run_search(
    query: str,
    version: str = "release",
    limit: int = 30,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
) -> str:
    """
    Run FTS5 search via the access layer (search.search_api).
    package_prefix and kind are optional filters. unique_classes: one entry per class with method_count.
    Returns JSON string or error dict.
    """
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    results, err = search.search_api(
        None,
        version,
        query.strip(),
        limit=limit,
        package_prefix=package_prefix or None,
        kind=kind or None,
        unique_classes=unique_classes,
    )
    if err is not None:
        return json.dumps(err, ensure_ascii=False)
    return json.dumps({
        "version": version,
        "term": query.strip(),
        "count": len(results),
        "results": results,
    }, ensure_ascii=False)


def _parse_fqcn(fqcn: str) -> tuple[str, str] | None:
    """If fqcn is 'com.hypixel.hytale.server.GameManager', returns ('com.hypixel.hytale.server', 'GameManager'). None if there is no dot."""
    s = (fqcn or "").strip()
    if not s or "." not in s:
        return None
    idx = s.rfind(".")
    return (s[:idx], s[idx + 1 :])


def _run_get_class(
    version: str,
    package: str | None = None,
    class_name: str | None = None,
    fqcn: str | None = None,
) -> str:
    """Return the exact class (package, class_name, kind, file_path) and all its methods. If fqcn is passed, package and class_name are derived. JSON or error."""
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    p = (package or "").strip()
    c = (class_name or "").strip()
    if (fqcn or "").strip():
        parsed = _parse_fqcn(fqcn)
        if parsed:
            p, c = parsed
    if not p or not c:
        return json.dumps({"error": "missing_params", "message": "Provide package and class_name, or fqcn (e.g. com.hypixel.hytale.server.GameManager)."}, ensure_ascii=False)
    root = config.get_project_root()
    db_path = config.get_db_path(root, version)
    if not db_path.is_file():
        return json.dumps({"error": "no_db", "message": f"Database for version {version} does not exist."}, ensure_ascii=False)
    with db.connection(db_path) as conn:
        data = db.get_class_and_methods(conn, p, c)
    if data is None:
        return json.dumps({"error": "not_found", "message": f"Class {p}.{c} not found."}, ensure_ascii=False)
    return json.dumps({"version": version, **data}, ensure_ascii=False)


def _run_list_classes(
    version: str,
    package_prefix: str,
    prefix_match: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """List classes by exact package or prefix. limit/offset for pagination. JSON: version, package_prefix, prefix_match, count, classes."""
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    p = (package_prefix or "").strip()
    if not p:
        return json.dumps({"error": "missing_param", "message": "package_prefix is required"}, ensure_ascii=False)
    limit = max(1, min(int(limit), 500)) if limit is not None else 100
    offset = max(0, int(offset)) if offset is not None else 0
    root = config.get_project_root()
    db_path = config.get_db_path(root, version)
    if not db_path.is_file():
        return json.dumps({"error": "no_db", "message": f"Database for version {version} does not exist."}, ensure_ascii=False)
    with db.connection(db_path) as conn:
        classes = db.list_classes(conn, p, prefix_match=prefix_match, limit=limit, offset=offset)
    return json.dumps({
        "version": version,
        "package_prefix": p,
        "prefix_match": prefix_match,
        "count": len(classes),
        "classes": classes,
    }, ensure_ascii=False)


def _run_context_list() -> str:
    """Return indexed versions and active version. JSON: indexed, active."""
    root = config.get_project_root()
    cfg = config.load_config(root)
    active = cfg.get(config.CONFIG_KEY_ACTIVE_SERVER) or "release"
    indexed = [
        v for v in config.VALID_SERVER_VERSIONS
        if config.get_db_path(root, v).is_file()
    ]
    return json.dumps({"indexed": indexed, "active": active}, ensure_ascii=False)


def _run_index_stats(version: str | None) -> str:
    """Return number of classes and methods for the version (or active). JSON or error."""
    root = config.get_project_root()
    if version is not None and version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    db_path = config.get_db_path(root, version)
    if not db_path.is_file():
        return json.dumps({
            "error": "no_db",
            "message": f"Database for version {version or 'active'} does not exist. Run prism index first.",
        }, ensure_ascii=False)
    resolved_version = version
    if resolved_version is None:
        cfg = config.load_config(root)
        resolved_version = cfg.get(config.CONFIG_KEY_ACTIVE_SERVER) or "release"
    with db.connection(db_path) as conn:
        classes, methods = db.get_stats(conn)
    return json.dumps({
        "version": resolved_version,
        "classes": classes,
        "methods": methods,
    }, ensure_ascii=False)


def _run_fts_help() -> str:
    """Return fixed text with FTS5 syntax for prism_search."""
    return (
        "FTS5 search syntax (prism_search):\n"
        "- Single word: matches that token.\n"
        "- Quoted phrase: \"exact phrase\" matches the exact phrase.\n"
        "- AND: term1 AND term2 (both must appear).\n"
        "- OR: term1 OR term2 (either can appear).\n"
        "- Prefix: term* matches tokens that start with 'term'.\n"
        "Examples: GameManager, \"getPlayer\" AND server, spawn OR despawn."
    )


def _run_read_source(
    version: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read the contents of a decompiled Java file. Validates path traversal. start_line/end_line are 1-based; if provided, returns only that range and total_lines."""
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    path_str = (file_path or "").strip().replace("\\", "/").lstrip("/")
    if not path_str:
        return json.dumps({"error": "missing_path", "message": "file_path is required"}, ensure_ascii=False)
    root = config.get_project_root()
    decompiled_dir = config.get_decompiled_dir(root, version).resolve()
    full_path = (decompiled_dir / path_str).resolve()
    if not full_path.is_relative_to(decompiled_dir):
        return json.dumps({"error": "invalid_path", "message": "file_path must be inside decompiled directory"}, ensure_ascii=False)
    if not full_path.is_file():
        return json.dumps({"error": "not_found", "message": f"File not found: {path_str}"}, ensure_ascii=False)
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return json.dumps({"error": "read_error", "message": str(e)}, ensure_ascii=False)
    lines = content.splitlines()
    total_lines = len(lines)
    payload: dict = {"content": content, "file_path": path_str, "version": version}
    if start_line is not None or end_line is not None:
        one = max(1, int(start_line) if start_line is not None else 1)
        two = min(total_lines, int(end_line) if end_line is not None else total_lines)
        if one > two:
            one, two = two, one
        payload["total_lines"] = total_lines
        payload["start_line"] = one
        payload["end_line"] = two
        payload["content"] = "\n".join(lines[one - 1 : two])
    return json.dumps(payload, ensure_ascii=False)


def _run_get_method(version: str, package: str, class_name: str, method_name: str) -> str:
    """Return the class and methods of that class whose name matches method_name (exact match, includes overloads). JSON or error."""
    if version not in config.VALID_SERVER_VERSIONS:
        version = "release"
    if not (package or "").strip() or not (class_name or "").strip() or not (method_name or "").strip():
        return json.dumps({"error": "missing_params", "message": "package, class_name and method_name are required"}, ensure_ascii=False)
    root = config.get_project_root()
    db_path = config.get_db_path(root, version)
    if not db_path.is_file():
        return json.dumps({"error": "no_db", "message": f"Database for version {version} does not exist."}, ensure_ascii=False)
    with db.connection(db_path) as conn:
        data = db.get_method(conn, package.strip(), class_name.strip(), method_name.strip())
    if data is None:
        return json.dumps({"error": "not_found", "message": f"Class {package}.{class_name} not found."}, ensure_ascii=False)
    return json.dumps({"version": version, **data}, ensure_ascii=False)


def _register_tools(app: FastMCP) -> None:
    """Register prism_* tools on the given FastMCP instance with localized descriptions."""

    def prism_search(
        query: str,
        version: str = "release",
        limit: int = 30,
        package_prefix: str | None = None,
        kind: str | None = None,
        unique_classes: bool = False,
    ) -> str:
        if not query or not str(query).strip():
            return json.dumps({"error": "missing_query", "message": "query is required"}, ensure_ascii=False)
        limit = max(1, min(int(limit), 500)) if limit is not None else 30
        return _run_search(query, version=version, limit=limit, package_prefix=package_prefix, kind=kind, unique_classes=unique_classes)

    prism_search.__doc__ = i18n.t("mcp.tools.prism_search.description")
    app.tool()(prism_search)

    def prism_get_class(
        version: str,
        package: str | None = None,
        class_name: str | None = None,
        fqcn: str | None = None,
    ) -> str:
        return _run_get_class(version, package=package, class_name=class_name, fqcn=fqcn)

    prism_get_class.__doc__ = i18n.t("mcp.tools.prism_get_class.description")
    app.tool()(prism_get_class)

    def prism_list_classes(
        version: str,
        package_prefix: str,
        prefix_match: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        return _run_list_classes(version, package_prefix, prefix_match, limit=limit, offset=offset)

    prism_list_classes.__doc__ = i18n.t("mcp.tools.prism_list_classes.description")
    app.tool()(prism_list_classes)

    def prism_context_list() -> str:
        return _run_context_list()

    prism_context_list.__doc__ = i18n.t("mcp.tools.prism_context_list.description")
    app.tool()(prism_context_list)

    def prism_index_stats(version: str | None = None) -> str:
        return _run_index_stats(version)

    prism_index_stats.__doc__ = i18n.t("mcp.tools.prism_index_stats.description")
    app.tool()(prism_index_stats)

    def prism_read_source(
        version: str,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        return _run_read_source(version, file_path, start_line=start_line, end_line=end_line)

    prism_read_source.__doc__ = i18n.t("mcp.tools.prism_read_source.description")
    app.tool()(prism_read_source)

    def prism_get_method(version: str, package: str, class_name: str, method_name: str) -> str:
        return _run_get_method(version, package, class_name, method_name)

    prism_get_method.__doc__ = i18n.t("mcp.tools.prism_get_method.description")
    app.tool()(prism_get_method)

    def prism_fts_help() -> str:
        return _run_fts_help()

    prism_fts_help.__doc__ = i18n.t("mcp.tools.prism_fts_help.description")
    app.tool()(prism_fts_help)


# Default instance for stdio (host/port unused)
mcp = FastMCP("orbis-prism")
_register_tools(mcp)


def run(
    transport: str = "stdio",
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """
    Start the MCP server. Uses stdio transport by default.
    If transport is "streamable-http", listens on host:port (useful for Docker).
    """
    if transport == "streamable-http":
        app = FastMCP("orbis-prism", host=host, port=port)
        _register_tools(app)
        server_to_run = app
    else:
        server_to_run = mcp
    try:
        if transport == "streamable-http":
            server_to_run.run(transport="streamable-http")
        else:
            server_to_run.run()
    except KeyboardInterrupt:
        pass  # Clean exit on close (Ctrl+C or client disconnect)
