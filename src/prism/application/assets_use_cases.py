# src/prism/application/assets_use_cases.py
import zipfile
from pathlib import Path
from typing import Callable, List, Optional
from ..infrastructure.assets_indexer import AssetIndexer
from ..ports.assets_repository import AssetsRepository
from ..domain.asset import Asset

class AssetsUseCases:
    """Orchestrates asset-related operations."""

    def __init__(self, repository: AssetsRepository):
        self.repository = repository

    def index_assets(
        self,
        db_path: Path,
        assets_zip_path: Path,
        version: str,
        progress_callback: Callable[[str, int, int], None] | None = None
    ) -> None:
        """Runs the indexer process."""
        indexer = AssetIndexer(db_path, assets_zip_path, version)
        indexer.run(progress_callback)

    def search_assets(
        self,
        db_path: Path,
        query: str,
        limit: int = 50
    ) -> List[Asset]:
        """Searches assets in the database."""
        return self.repository.search_assets(db_path, query, limit)

    def get_asset_info(self, db_path: Path, path: str) -> Optional[Asset]:
        """Gets detailed info about an asset."""
        return self.repository.get_asset_by_path(db_path, path)

    def inspect_asset_file(
        self,
        assets_zip_path: Path,
        asset_path: str
    ) -> bytes | None:
        """Extracts the bytes of a specific file from the ZIP without extracting everything."""
        if not assets_zip_path.exists():
            return None
        
        try:
            with zipfile.ZipFile(assets_zip_path, 'r') as z:
                #_ zipfile.ZipFile.open expects a ZIP-style path (forward slashes)
                zp = asset_path.replace('\\', '/')
                if zp in z.namelist():
                    with z.open(zp) as f:
                        return f.read()
        except Exception:
            pass
        return None
