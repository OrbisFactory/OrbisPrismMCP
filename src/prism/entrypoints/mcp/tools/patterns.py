# src/prism/entrypoints/mcp/tools/patterns.py
import json
from mcp.server.fastmcp import FastMCP
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ....application.pattern_service import PatternService

def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    pattern_service = PatternService(repository)

    @app.tool()
    def prism_detect_patterns(package: str, class_name: str, version: str = "release") -> str:
        """
        Detecta patrones de diseño (Singleton, Factory, ECS) en una clase específica.
        """
        root = config.get_project_root()
        db_path = config.get_db_path(root, version)
        patterns = pattern_service.detect_patterns(db_path, package, class_name)
        return json.dumps({
            "package": package,
            "class_name": class_name,
            "patterns": patterns
        }, ensure_ascii=False)
