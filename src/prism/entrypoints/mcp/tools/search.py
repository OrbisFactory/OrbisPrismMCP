# src/prism/entrypoints/mcp/tools/search.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import search_api as app_search_api
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the prism_search tool."""

    def prism_search(
        query: str,
        version: str = "release",
        limit: int = 30,
        package_prefix: str | None = None,
        layer: str | None = None,
        kind: str | None = None,
        unique_classes: bool = False,
    ) -> str:
        if not query or not str(query).strip():
            return json.dumps({"error": "missing_query", "message": "query is required"}, ensure_ascii=False)
        
        limit = max(1, min(int(limit), 500)) if limit is not None else 30
        norm_version = normalize_version(version)

        #_ Layer mapping to packages
        layer_map = {
            "core": "com.hypixel.hytale.server.core",
            "plugins": "com.hypixel.hytale.builtin",
            "npc": "com.hypixel.hytale.server.npc",
            "ui": "com.hypixel.hytale.server.core.ui"
        }
        
        effective_prefix = package_prefix
        if layer and layer.lower() in layer_map:
            effective_prefix = layer_map[layer.lower()]
        
        results, err = app_search_api(
            config,
            repository,
            None,
            norm_version,
            query.strip(),
            limit=limit,
            package_prefix=effective_prefix,
            kind=kind or None,
            unique_classes=unique_classes,
            t=i18n.t,
        )

        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        
        return json.dumps({
            "version": norm_version,
            "term": query.strip(),
            "count": len(results),
            "results": results,
        }, ensure_ascii=False)

    prism_search.__doc__ = i18n.t("mcp.tools.prism_search.description")
    app.tool()(prism_search)
