# src/prism/entrypoints/mcp/tools/usages.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import find_usages as app_find_usages
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository


def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the prism_find_usages tool."""

    def prism_find_usages(
        version: str,
        target_class: str,
        limit: int = 100,
    ) -> str:
        norm_version = normalize_version(version)
        results, err = app_find_usages(config, None, norm_version, target_class, limit=limit)
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps({
            "version": norm_version,
            "target_class": target_class,
            "count": len(results),
            "usages": results,
        }, ensure_ascii=False)

    prism_find_usages.__doc__ = i18n.t("mcp.tools.prism_find_usages.description")
    app.tool()(prism_find_usages)
