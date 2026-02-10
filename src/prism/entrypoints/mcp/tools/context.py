# src/prism/entrypoints/mcp/tools/context.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import (
    get_context_list as app_get_context_list,
    get_index_stats as app_get_index_stats,
)
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository


def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers context and index statistics tools."""

    def prism_context_list() -> str:
        ctx = app_get_context_list(config, None)
        return json.dumps(ctx, ensure_ascii=False)

    prism_context_list.__doc__ = i18n.t("mcp.tools.prism_context_list.description")
    app.tool()(prism_context_list)

    def prism_index_stats(version: str | None = None) -> str:
        if version and str(version).strip():
            version = normalize_version(version)
        data, err = app_get_index_stats(config, repository, None, version)
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    prism_index_stats.__doc__ = i18n.t("mcp.tools.prism_index_stats.description")
    app.tool()(prism_index_stats)
