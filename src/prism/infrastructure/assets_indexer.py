# src/prism/infrastructure/assets_indexer.py
import json
import zipfile
from pathlib import Path
from typing import Callable

from . import db

class AssetIndexer:
    """Indexes Hytale assets from Assets.zip without full extraction."""

    def __init__(self, db_path: Path, assets_zip_path: Path, version: str):
        self.db_path = db_path
        self.assets_zip_path = assets_zip_path
        self.version = version

    def run(self, progress_callback: Callable[[str, int, int], None] | None = None):
        """Iterates over the ZIP and indexes relevant files."""
        if not self.assets_zip_path.exists():
            return

        with zipfile.ZipFile(self.assets_zip_path, 'r') as z:
            all_files = z.namelist()
            total = len(all_files)
            
            with db.connection(self.db_path) as conn:
                db.init_assets_schema(conn)
                
                for i, file_path in enumerate(all_files):
                    info = z.getinfo(file_path)
                    if info.is_dir():
                        continue
                    
                    ext = Path(file_path).suffix.lower()
                    metadata = None
                    
                    #_ Index metadata for JSON-like files
                    if ext in ('.json', '.blockyanim', '.item', '.recipe', '.entity'):
                        try:
                            with z.open(file_path) as f:
                                content = f.read().decode('utf-8')
                                #_ We try to extract key fields to make them easily searchable
                                #_ For now, we store the whole JSON to search inside it via FTS
                                metadata = content
                        except Exception:
                            pass
                    
                    #_ For images, we just index the entry
                    #_ (In a future step we could extract dimensions from headers)
                    
                    db.insert_asset(
                        conn,
                        path=file_path,
                        extension=ext,
                        size=info.file_size,
                        metadata=metadata,
                        version=self.version
                    )
                    
                    if progress_callback and i % 100 == 0:
                        progress_callback(file_path, i, total)
                
                conn.commit()
