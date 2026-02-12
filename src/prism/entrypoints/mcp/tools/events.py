# src/prism/entrypoints/mcp/tools/events.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import list_events as app_list_events
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers event discovery tools."""

    def prism_get_events(
        version: str = "release",
        limit: int = 100,
    ) -> str:
        norm_version = normalize_version(version)
        limit = max(1, min(int(limit), 500))
        
        data, err = app_list_events(config, repository, None, norm_version, limit)
        if err: return json.dumps(err, ensure_ascii=False)
        
        return json.dumps({
            "version": norm_version,
            "count_classes": len(data["event_classes"]),
            "count_subscriptions": len(data["subscriptions"]),
            **data
        }, ensure_ascii=False)

    prism_get_events.__doc__ = i18n.t("mcp.tools.prism_get_events.description")
    app.tool()(prism_get_events)
