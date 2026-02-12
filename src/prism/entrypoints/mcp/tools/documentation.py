# src/prism/entrypoints/mcp/tools/documentation.py
from mcp.server.fastmcp import FastMCP
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.documentation_service import DocumentationService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    #_ Inicializar el servicio de documentación apuntando a los recursos
    resource_path = config.get_project_root() / "src" / "prism" / "resources"
    doc_service = DocumentationService(resource_path)

    @app.tool()
    def prism_explain_concept(concept: str) -> str:
        """
        Proporciona una explicación detallada de un concepto de Hytale (ej. 'ECS', 'Teleport').
        """
        return doc_service.explain_concept(concept)
