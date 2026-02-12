# src/prism/entrypoints/mcp/bootstrap.py
from mcp.server.fastmcp import FastMCP
from ...ports.config_provider import ConfigProvider
from ...ports.index_repository import IndexRepository
from .tools import context, class_details, listing, search, source, usages, documentation, ecs, snippets, patterns

def register_all_tools(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers all Prism tools with the FastMCP instance."""
    context.register(app, config, repository)
    class_details.register(app, config, repository)
    listing.register(app, config, repository)
    search.register(app, config, repository)
    source.register(app, config, repository)
    usages.register(app, config, repository)
    documentation.register(app, config, repository)
    ecs.register(app, config, repository)
    snippets.register(app, config, repository)
    patterns.register(app, config, repository)
