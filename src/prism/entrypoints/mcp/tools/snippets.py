# src/prism/entrypoints/mcp/tools/snippets.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.snippet_service import SnippetService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the usage snippets tool."""
    
    def prism_get_usage_snippet(version: str, file_path: str, target_string: str, window: int = 10) -> str:
        root = config.get_project_root()
        result = SnippetService.get_snippet(config, root, version, file_path, target_string, window)
        return json.dumps(result, ensure_ascii=False)

    prism_get_usage_snippet.__doc__ = i18n.t("mcp.tools.prism_get_usage_snippet.description")
    app.tool()(prism_get_usage_snippet)
