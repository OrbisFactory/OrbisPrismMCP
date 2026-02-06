# ConfigProvider implementation using .prism.json and environment.

from pathlib import Path

from . import config as _config


class FileConfigProvider:
    """Implements ConfigProvider using the existing config module."""

    def get_project_root(self) -> Path:
        return _config.get_project_root()

    def get_db_path(self, root: Path | None, version: str | None) -> Path:
        return _config.get_db_path(root, version)

    def get_decompiled_dir(self, root: Path | None, version: str) -> Path:
        return _config.get_decompiled_dir(root, version)

    def load_config(self, root: Path | None) -> dict:
        return _config.load_config(root)
