# Ports (interfaces) for dependency inversion.

from .config_provider import ConfigProvider
from .index_repository import IndexRepository

__all__ = ["ConfigProvider", "IndexRepository"]
