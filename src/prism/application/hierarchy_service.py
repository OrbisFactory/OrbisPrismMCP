# src/prism/application/hierarchy_service.py
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider, IndexRepository


def find_implementations(
    config_provider: "ConfigProvider",
    index_repository: "IndexRepository",
    root: Path | None,
    version: str,
    target_name: str,
    limit: int = 100,
) -> tuple[list[dict] | None, dict | None]:
    """
    Find classes that implement/extend target_name.
    Returns (results, None) or (None, error_dict).
    """
    from ..domain.constants import normalize_version

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    db_path = config_provider.get_db_path(root, version)
    
    if not db_path.is_file():
        return (None, {"error": "no_db", "message": f"Database for version {version} does not exist."})

    results = index_repository.find_implementations(db_path, target_name, limit)
    return (results, None)
