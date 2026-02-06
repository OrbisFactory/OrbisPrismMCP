# Servidor MCP para Orbis Prism (SDK oficial: https://github.com/modelcontextprotocol/python-sdk).
# Expone el tool prism_search para buscar en la API indexada de Hytale.
# Compatible con mcp>=1.0 (v1.x usa FastMCP; v2 usa MCPServer).
# Transporte: stdio (por defecto) o streamable-http (útil para Docker).

import json

from mcp.server.fastmcp import FastMCP

from . import config
from . import db
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
    Ejecuta búsqueda FTS5 mediante la capa de acceso (search.search_api).
    package_prefix y kind son filtros opcionales. unique_classes: una entrada por clase con method_count.
    Devuelve JSON string o dict de error.
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
    """Si fqcn es 'com.hypixel.hytale.server.GameManager', devuelve ('com.hypixel.hytale.server', 'GameManager'). None si no hay al menos un punto."""
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
    """Devuelve la clase exacta (package, class_name, kind, file_path) y todos sus métodos. Si se pasa fqcn, se deriva package y class_name. JSON o error."""
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
    """Lista clases por paquete exacto o por prefijo. limit/offset para paginación. JSON: version, package_prefix, prefix_match, count, classes."""
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
    """Devuelve versiones indexadas y versión activa. JSON: indexed, active."""
    root = config.get_project_root()
    cfg = config.load_config(root)
    active = cfg.get(config.CONFIG_KEY_ACTIVE_SERVER) or "release"
    indexed = [
        v for v in config.VALID_SERVER_VERSIONS
        if config.get_db_path(root, v).is_file()
    ]
    return json.dumps({"indexed": indexed, "active": active}, ensure_ascii=False)


def _run_index_stats(version: str | None) -> str:
    """Devuelve número de clases y métodos para la versión (o activa). JSON o error."""
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
    """Devuelve texto fijo con sintaxis FTS5 para prism_search."""
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
    """Lee el contenido de un archivo Java descompilado. Valida path traversal. start_line/end_line son 1-based; si se pasan, se devuelve solo ese rango y total_lines."""
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
    """Devuelve la clase y los métodos de esa clase cuyo nombre coincide con method_name (coincidencia exacta, incluye sobrecargas). JSON o error."""
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
    """Registra las tools prism_* en la instancia FastMCP dada."""

    @app.tool()
    def prism_search(
        query: str,
        version: str = "release",
        limit: int = 30,
        package_prefix: str | None = None,
        kind: str | None = None,
        unique_classes: bool = False,
    ) -> str:
        """Search the indexed Hytale API (FTS5). Returns matching methods (or one row per class if unique_classes=True) with file_path for source code.
        FTS5 syntax: single word or quoted phrase; multiple terms: term1 AND term2; OR for alternatives. Use prism_fts_help for full syntax.
        Optional: package_prefix (e.g. com.hypixel.hytale.server), kind (class, interface, record, enum), unique_classes (one entry per class with method_count).
        For exact class when you know FQCN, prefer prism_get_class."""
        if not query or not str(query).strip():
            return json.dumps({"error": "missing_query", "message": "query is required"}, ensure_ascii=False)
        limit = max(1, min(int(limit), 500)) if limit is not None else 30
        return _run_search(query, version=version, limit=limit, package_prefix=package_prefix, kind=kind, unique_classes=unique_classes)

    @app.tool()
    def prism_get_class(
        version: str,
        package: str | None = None,
        class_name: str | None = None,
        fqcn: str | None = None,
    ) -> str:
        """Get the exact class by package and class name (or by fqcn, e.g. com.hypixel.hytale.server.GameManager) with all its methods. Returns package, class_name, kind, file_path, and methods list (method, returns, params, is_static, annotation). Provide either (package + class_name) or fqcn."""
        return _run_get_class(version, package=package, class_name=class_name, fqcn=fqcn)

    @app.tool()
    def prism_list_classes(
        version: str,
        package_prefix: str,
        prefix_match: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """List all classes in a package. package_prefix is the full package (e.g. com.hypixel.hytale.server). If prefix_match is True, includes subpackages. Use limit (default 100, max 500) and offset for pagination. Returns version, package_prefix, count, and classes (package, class_name, kind, file_path)."""
        return _run_list_classes(version, package_prefix, prefix_match, limit=limit, offset=offset)

    @app.tool()
    def prism_context_list() -> str:
        """List indexed server versions (release, prerelease) and the active context. Use to discover what is available before searching."""
        return _run_context_list()

    @app.tool()
    def prism_index_stats(version: str | None = None) -> str:
        """Return the number of indexed classes and methods for a version. If version is omitted, uses the active context."""
        return _run_index_stats(version)

    @app.tool()
    def prism_read_source(
        version: str,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """Read the contents of a decompiled Java source file. file_path is the relative path from the decompiled directory (e.g. from prism_search result). Optional start_line and end_line (1-based) return only that range; response includes total_lines and the requested range."""
        return _run_read_source(version, file_path, start_line=start_line, end_line=end_line)

    @app.tool()
    def prism_get_method(version: str, package: str, class_name: str, method_name: str) -> str:
        """Get methods of a class that match the given method name (exact match; includes overloads with different params). Returns package, class_name, kind, file_path, and methods list (method, returns, params, is_static, annotation). Use when you need a specific method of a known class."""
        return _run_get_method(version, package, class_name, method_name)

    @app.tool()
    def prism_fts_help() -> str:
        """Return a short reference for FTS5 search syntax used by prism_search: single word, quoted phrase, AND/OR, prefix, and examples."""
        return _run_fts_help()


# Instancia por defecto para stdio (host/port no se usan)
mcp = FastMCP("orbis-prism")
_register_tools(mcp)


def run(
    transport: str = "stdio",
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """
    Arranca el servidor MCP. Por defecto usa transporte stdio.
    Si transport es "streamable-http", escucha en host:port (útil para Docker).
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
        pass  # Salida limpia al cerrar (Ctrl+C o cliente desconecta)
