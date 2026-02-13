# src/prism/domain/asset.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Asset:
    path: str
    extension: str
    size: int
    version: str
    category: Optional[str] = None
    internal_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    metadata: Optional[str] = None

    @property
    def name(self) -> str:
        return self.path.split('/')[-1]
