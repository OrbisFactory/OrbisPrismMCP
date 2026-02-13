# Workspace cleanup: delete DB, build artifacts, and complete reset.

import shutil
from pathlib import Path

from ..domain.constants import VALID_SERVER_VERSIONS
from . import config_impl


def clean_db(root: Path | None = None) -> None:
    """
    Deletes the SQLite databases from the workspace (prism_api_release.db and prism_api_prerelease.db).
    Does not delete other files from the db directory.
    """
    root = root or config_impl.get_project_root()
    db_dir = config_impl.get_db_dir(root)
    if not db_dir.is_dir():
        return
    for version in VALID_SERVER_VERSIONS:
        db_path = config_impl.get_db_path(root, version)
        if db_path.is_file():
            db_path.unlink()


def clean_build(root: Path | None = None) -> None:
    """
    Deletes build artifact directories: sources/<version> and decompiled/<version>
    for release and prerelease. Only deletes them if they exist.
    """
    root = root or config_impl.get_project_root()
    for version in VALID_SERVER_VERSIONS:
        sources_dir = config_impl.get_sources_dir(root, version)
        if sources_dir.is_dir():
            shutil.rmtree(sources_dir)
        decompiled_dir = config_impl.get_decompiled_dir(root, version)
        if decompiled_dir.is_dir():
            shutil.rmtree(decompiled_dir)


def reset_workspace(root: Path | None = None) -> None:
    """
    Resets the project to zero: runs clean_db and clean_build, and removes .prism.json
    so the user can run context detect and init again from the beginning.
    """
    root = root or config_impl.get_project_root()
    clean_db(root)
    clean_build(root)
    config_path = config_impl.get_config_path(root)
    if config_path.is_file():
        config_path.unlink()
