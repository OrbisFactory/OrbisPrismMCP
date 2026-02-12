# src/prism/entrypoints/mcp/tools/analysis.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import get_call_flow as app_get_call_flow
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers advanced analysis tools."""

    def prism_call_flow(
        target_class: str,
        method_name: str,
        version: str = "release",
        limit: int = 100,
    ) -> str:
        norm_version = normalize_version(version)
        limit = max(1, min(int(limit), 500))
        
        data, err = app_get_call_flow(config, repository, None, norm_version, target_class, method_name, limit)
        if err: return json.dumps(err, ensure_ascii=False)
        
        return json.dumps(data, ensure_ascii=False)

    prism_call_flow.__doc__ = i18n.t("mcp.tools.prism_call_flow.description")
    app.tool()(prism_call_flow)
