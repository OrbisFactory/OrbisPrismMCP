# src/prism/ports/assets_repository.py
from pathlib import Path
from typing import Protocol, List, Optional
from ..domain.asset import Asset

class AssetsRepository(Protocol):
    """Port for asset storage and retrieval."""
    
    def search_assets(self, db_path: Path, query: str, limit: int = 50) -> List[Asset]:
        """Search assets via FTS5."""
        ...

    def get_asset_by_path(self, db_path: Path, path: str) -> Optional[Asset]:
        """Get a specific asset by its path."""
        ...
