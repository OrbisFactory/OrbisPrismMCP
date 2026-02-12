# src/prism/application/event_service.py
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider, IndexRepository


def list_events(
    config_provider: "ConfigProvider",
    index_repository: "IndexRepository",
    root: Path | None,
    version: str,
    limit: int = 100,
) -> tuple[dict | None, dict | None]:
    """
    List events and subscriptions.
    """
    from ..domain.constants import normalize_version

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    db_path = config_provider.get_db_path(root, version)
    
    if not db_path.is_file():
        return (None, {"error": "no_db", "message": f"Database for version {version} does not exist."})

    data = index_repository.list_events(db_path, limit)
    return (data, None)
