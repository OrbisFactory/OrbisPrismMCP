# src/prism/entrypoints/mcp/tools/documentation.py
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.documentation_service import DocumentationService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    #_ Initialize documentation service pointing to resources
    resource_path = config.get_project_root() / "src" / "prism" / "resources"
    doc_service = DocumentationService(resource_path)

    def prism_explain_concept(concept: str) -> str:
        return doc_service.explain_concept(concept, t=i18n.t)

    prism_explain_concept.__doc__ = i18n.t("mcp.tools.prism_explain_concept.description")
    app.tool()(prism_explain_concept)
