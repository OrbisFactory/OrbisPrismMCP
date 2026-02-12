# src/prism/entrypoints/mcp/tools/hierarchy.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import get_hierarchy as app_get_hierarchy
from ....application import find_implementations as app_find_implementations
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers hierarchy tools."""

    def prism_get_hierarchy(
        version: str = "release",
        package: str | None = None,
        class_name: str | None = None,
        fqcn: str | None = None,
    ) -> str:
        norm_version = normalize_version(version)
        #_ fqcn support
        effective_pkg = package
        effective_cls = class_name
        if fqcn:
            parts = fqcn.rsplit(".", 1)
            if len(parts) == 2:
                effective_pkg, effective_cls = parts
            else:
                return json.dumps({"error": "invalid_fqcn", "message": "FQCN must be package.Class"}, ensure_ascii=False)
        
        if not effective_pkg or not effective_cls:
            return json.dumps({"error": "missing_params", "message": "package and class_name or fqcn are required"}, ensure_ascii=False)

        result = app_get_hierarchy(config, norm_version, effective_pkg, effective_cls, None)
        return json.dumps(result, ensure_ascii=False)

    def prism_find_implementations(
        target_class: str,
        version: str = "release",
        limit: int = 50,
    ) -> str:
        norm_version = normalize_version(version)
        limit = max(1, min(int(limit), 500))
        results, err = app_find_implementations(config, repository, None, norm_version, target_class, limit)
        if err: return json.dumps(err, ensure_ascii=False)
        return json.dumps({
            "version": norm_version,
            "target": target_class,
            "count": len(results),
            "results": results
        }, ensure_ascii=False)

    prism_get_hierarchy.__doc__ = i18n.t("mcp.tools.prism_get_hierarchy.description")
    app.tool()(prism_get_hierarchy)

    prism_find_implementations.__doc__ = i18n.t("mcp.tools.prism_find_implementations.description")
    app.tool()(prism_find_implementations)
