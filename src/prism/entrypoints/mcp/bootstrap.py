# src/prism/entrypoints/mcp/bootstrap.py
from mcp.server.fastmcp import FastMCP
from ...ports.config_provider import ConfigProvider
from ...ports.index_repository import IndexRepository
from ...ports.assets_repository import AssetsRepository
from .tools import context, class_details, listing, search, source, usages, documentation, ecs, snippets, patterns, hierarchy, events, analysis, assets

def register_all_tools(app: FastMCP, config: ConfigProvider, repository: IndexRepository, assets_repo: AssetsRepository):
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
    hierarchy.register(app, config, repository)
    events.register(app, config, repository)
    analysis.register(app, config, repository)
    assets.register(app, config, assets_repo)
