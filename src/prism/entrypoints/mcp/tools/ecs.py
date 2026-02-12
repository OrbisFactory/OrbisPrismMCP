# src/prism/entrypoints/mcp/tools/ecs.py
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.ecs_service import ECSService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the ECS exploration tools."""
    ecs_service = ECSService(repository)

    def prism_find_system_for_component(component_name: str, version: str = "release") -> list[dict]:
        root = config.get_project_root()
        db_path = config.get_db_path(root, version)
        return ecs_service.find_systems_for_component(db_path, component_name)

    prism_find_system_for_component.__doc__ = i18n.t("mcp.tools.prism_find_system_for_component.description")
    app.tool()(prism_find_system_for_component)
