# src/prism/entrypoints/mcp/tools/snippets.py
import json
from mcp.server.fastmcp import FastMCP
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.snippet_service import SnippetService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    @app.tool()
    def prism_get_usage_snippet(version: str, file_path: str, target_string: str, window: int = 10) -> str:
        """
        Obtiene un fragmento de código de un archivo alrededor de una cadena específica (ej. nombre de clase o método).
        """
        root = config.get_project_root()
        result = SnippetService.get_snippet(config, root, version, file_path, target_string, window)
        return json.dumps(result, ensure_ascii=False)
