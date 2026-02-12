# src/prism/entrypoints/mcp/tools/patterns.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.pattern_service import PatternService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the design patterns detection tool."""
    pattern_service = PatternService(repository)

    def prism_detect_patterns(package: str, class_name: str, version: str = "release") -> str:
        root = config.get_project_root()
        db_path = config.get_db_path(root, version)
        patterns = pattern_service.detect_patterns(db_path, package, class_name)
        return json.dumps({
            "package": package,
            "class_name": class_name,
            "patterns": patterns
        }, ensure_ascii=False)

    prism_detect_patterns.__doc__ = i18n.t("mcp.tools.prism_detect_patterns.description")
    app.tool()(prism_detect_patterns)
