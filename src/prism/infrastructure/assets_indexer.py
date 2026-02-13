# src/prism/infrastructure/assets_indexer.py
import json
import zipfile
import struct
from pathlib import Path
from typing import Callable

from . import db

class AssetIndexer:
    """Indexes Hytale assets from Assets.zip without full extraction."""

    #_ Map based on Hytale's internal AssetRegistryLoader
    CATEGORY_MAP = {
        "Audio/AmbienceFX": "AmbienceFX",
        "Item/Block/Hitboxes": "BlockHitbox",
        "Item/Block/Sets": "BlockSet",
        "Item/Block/Sounds": "BlockSound",
        "Audio/ItemSounds": "ItemSound",
        "Item/Block/Particles": "BlockParticle",
        "Item/Block/BreakingDecals": "BlockDecal",
        "Item/Block/Blocks": "Block",
        "Item/Block/Fluids": "Fluid",
        "Item/Animations": "ItemAnimation",
        "Environments": "Environment",
        "Item/Category/CreativeLibrary": "CreativeCategory",
        "Item/Category/Fieldcraft": "FieldcraftCategory",
        "Drops": "Drop",
        "WordLists": "WordList",
        "Item/Reticles": "Reticle",
        "PortalTypes": "Portal",
        "Item/Items": "Item",
        "Item/Recipes": "Recipe",
        "Models": "Model",
        "Particles": "Particle",
        "Entity/Trails": "Trail",
        "Projectiles": "Projectile",
        "Entity/Effects": "Effect",
        "Entity/ModelVFX": "ModelVFX",
        "Entity/GameMode": "GameMode",
        "Item/ResourceTypes": "ResourceType",
        "Weathers": "Weather",
        "GameplayConfigs": "GameplayConfig",
        "Audio/SoundEvents": "SoundEvent",
        "Audio/SoundSets": "SoundSet",
        "Audio/AudioCategories": "AudioCategory",
        "Audio/Reverb": "Reverb",
        "Audio/EQ": "EQ",
        "ResponseCurves": "ResponseCurve",
        "Item/Qualities": "ItemQuality",
        "Entity/Damage": "DamageType",
        "ProjectileConfigs": "ProjectileConfig",
        "Item/Groups": "ItemGroup",
        "Camera/CameraEffect": "CameraEffect",
        "TagPatterns": "TagPattern",
        "BlockTextures": "BlockTexture",
        "Items": "ItemTexture",
        "Characters": "CharacterTexture",
        "Sky": "SkyTexture",
        "UI": "UITexture",
    }

    def __init__(self, db_path: Path, assets_zip_path: Path, version: str):
        self.db_path = db_path
        self.assets_zip_path = assets_zip_path
        self.version = version

    def _determine_category(self, file_path: str) -> str | None:
        p = Path(file_path)
        #_ Check parents to find a match in CATEGORY_MAP (longest match priority)
        #_ We normalize to posix for consistent mapping
        posix_path = p.as_posix()
        
        #_ Try to find the most specific directory match
        for folder, category in self.CATEGORY_MAP.items():
            if posix_path.startswith(folder + "/"):
                return category
        return None

    def _get_png_dimensions(self, data: bytes) -> tuple[int, int] | None:
        """Extracts width and height from PNG header (first 24 bytes)."""
        if len(data) < 24: return None
        if data[0:8] != b'\x89PNG\r\n\x1a\n': return None
        #_ Width and height are 4-byte big-endian integers starting at offset 16
        try:
            width, height = struct.unpack('>II', data[16:24])
            return width, height
        except Exception:
            return None

    def run(self, progress_callback: Callable[[str, int, int], None] | None = None):
        """Iterates over the ZIP and indexes relevant files."""
        if not self.assets_zip_path.exists():
            return

        with zipfile.ZipFile(self.assets_zip_path, 'r') as z:
            all_files = z.namelist()
            total = len(all_files)
            
            with db.connection(self.db_path) as conn:
                db.init_assets_schema(conn)
                
                #_ Batch speed up
                for i, file_path in enumerate(all_files):
                    info = z.getinfo(file_path)
                    if info.is_dir():
                        continue
                    
                    ext = Path(file_path).suffix.lower()
                    metadata = None
                    category = self._determine_category(file_path)
                    internal_id = None
                    width = None
                    height = None
                    
                    #_ Index metadata for JSON-like files
                    if ext in ('.json', '.blockyanim', '.item', '.recipe', '.entity', '.particlespawner', '.particlesystem'):
                        try:
                            with z.open(file_path) as f:
                                #_ Limit size to avoid memory issues with huge files
                                raw = f.read(1024 * 512) # 512KB limit for metadata indexing
                                content = raw.decode('utf-8', errors='ignore')
                                metadata = content
                                
                                #_ Try to extract internal ID from JSON
                                try:
                                    #_ Fast extraction for common Hytale files
                                    if '"id":' in content:
                                        data = json.loads(content)
                                        if isinstance(data, dict):
                                            internal_id = data.get('id')
                                            #_ If it's a block, it might have a group or type we want
                                            if not category:
                                                category = data.get('type')
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    
                    #_ For images, extract dimensions
                    elif ext == '.png':
                        try:
                            with z.open(file_path) as f:
                                header = f.read(24)
                                dims = self._get_png_dimensions(header)
                                if dims:
                                    width, height = dims
                        except Exception:
                            pass
                    
                    db.insert_asset(
                        conn,
                        path=file_path,
                        extension=ext,
                        size=info.file_size,
                        category=category,
                        internal_id=internal_id,
                        width=width,
                        height=height,
                        metadata=metadata,
                        version=self.version
                    )
                    
                    if progress_callback and i % 500 == 0:
                        progress_callback(file_path, i, total)
                
                conn.commit()
