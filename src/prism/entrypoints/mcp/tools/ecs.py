# src/prism/entrypoints/mcp/tools/ecs.py
from mcp.server.fastmcp import FastMCP
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.ecs_service import ECSService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    ecs_service = ECSService(repository)

    @app.tool()
    def prism_find_system_for_component(component_name: str, version: str = "release") -> list[dict]:
        """
        Busca sistemas que procesan una componente específica basándose en parámetros de métodos.
        """
        root = config.get_project_root()
        db_path = config.get_db_path(root, version)
        return ecs_service.find_systems_for_component(db_path, component_name)
