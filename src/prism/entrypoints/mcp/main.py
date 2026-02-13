# src/prism/entrypoints/mcp/main.py
from mcp.server.fastmcp import FastMCP
from ...infrastructure.file_config import FileConfigProvider
from ...infrastructure.sqlite_repository import SqliteIndexRepository
from ...infrastructure.sqlite_assets_repository import SqliteAssetsRepository
from .bootstrap import register_all_tools

def run(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
    """
    Starts the MCP server. Uses stdio transport by default.
    If transport is "sse", listens on host:port.
    """
    config_provider = FileConfigProvider()
    index_repository = SqliteIndexRepository()
    assets_repository = SqliteAssetsRepository()
    
    app = FastMCP("orbis-prism", host=host, port=port)
    
    # Register all tools, injecting dependencies.
    register_all_tools(app, config_provider, index_repository, assets_repository)
    
    try:
        app.run(transport=transport)
    except KeyboardInterrupt:
        pass
