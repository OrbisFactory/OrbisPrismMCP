# Central configuration: default paths, constants, and environment variables.

import json
import os
from pathlib import Path

from ..domain.constants import VALID_SERVER_VERSIONS

# Hytale server JAR filename
HYTALE_JAR_NAME = "HytaleServer.jar"

# Core packages kept after pruning
CORE_PACKAGE_PATHS = [
    "com/hypixel/hytale",
    "com/hypixel/fastutil",
]

# Environment variables (BluePrint / convention)
ENV_JAR_PATH = "HYTALE_JAR_PATH"
ENV_OUTPUT_DIR = "PRISM_OUTPUT_DIR"
ENV_OUTPUT_DIR = "PRISM_OUTPUT_DIR"
ENV_LANG = "PRISM_LANG"
ENV_WORKSPACE = "PRISM_WORKSPACE"
ENV_DB_DIR = "PRISM_DB_DIR"
ENV_DB_PATH_RELEASE = "PRISM_DB_PATH_RELEASE"
ENV_DB_PATH_PRERELEASE = "PRISM_DB_PATH_PRERELEASE"
ENV_JADX_URL = "PRISM_JADX_URL"

# Config file names (project root)
CONFIG_FILENAME = ".prism.json"
CONFIG_KEY_JAR_PATH = "jar_path"
CONFIG_KEY_JAR_PATH_PRERELEASE = "jar_path_prerelease"
CONFIG_KEY_JAR_PATH_RELEASE = "jar_path_release"
CONFIG_KEY_OUTPUT_DIR = "output_dir"
CONFIG_KEY_OUTPUT_DIR = "output_dir"
CONFIG_KEY_LANG = "lang"
CONFIG_KEY_ACTIVE_SERVER = "active_server"
CONFIG_KEY_JADX_PATH = "jadx_path"


#_ JADX Decompiler (Fat JAR from Maven Central)
JADX_VERSION = "1.5.3"
JADX_URL = f"https://github.com/skylot/jadx/releases/download/v{JADX_VERSION}/jadx-{JADX_VERSION}.zip"
JADX_JAR_NAME = f"jadx-{JADX_VERSION}-all.jar"


def get_project_root() -> Path:
    """Project root: folder containing .prism.json, or fallback to global home."""
    # 1. Check environment variable
    env_root = os.environ.get(ENV_WORKSPACE)
    if env_root:
        p = Path(env_root).resolve()
        if p.is_dir():
            return p
            
    # 2. Search upwards for .prism.json starting from CWD
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / CONFIG_FILENAME).exists():
            return current
        current = current.parent
        
    # 3. Fallback to global home directory (~/.prism)
    global_home = Path.home() / ".prism"
    return global_home.resolve()


def get_workspace_dir(root: Path | None = None) -> Path:
    """Workspace directory (decompiled, db, server)."""
    root = root or get_project_root()
    env_dir = os.environ.get(ENV_OUTPUT_DIR)
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    return root / "workspace"


def get_bin_dir(root: Path | None = None) -> Path:
    """Binary directory (for tools like Procyon)."""
    return get_workspace_dir(root) / "bin"


def get_config_path(root: Path | None = None) -> Path:
    """Path to the persistent configuration file."""
    root = root or get_project_root()
    return root / CONFIG_FILENAME


def load_config(root: Path | None = None) -> dict:
    """Load config from .prism.json. Returns empty dict if not found."""
    path = get_config_path(root)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict, root: Path | None = None) -> None:
    """Save config to .prism.json."""
    path = get_config_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_jar_path_from_config(root: Path | None = None) -> Path | None:
    """Gets JAR path from config. None if not defined."""
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JAR_PATH)
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def get_jar_path_release_from_config(root: Path | None = None) -> Path | None:
    """Release version JAR. Infers from jar_path or sibling if needed."""
    root = root or get_project_root()
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JAR_PATH_RELEASE)
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
    jar = get_jar_path_from_config(root)
    if jar is None:
        return None
    s = str(jar).replace("\\", "/")
    if "release" in s:
        return jar
    if "pre-release" in s:
        from . import detection
        return detection.get_sibling_version_jar_path(jar)
    return jar


def get_jar_path_prerelease_from_config(root: Path | None = None) -> Path | None:
    """Prerelease version JAR. Infers from jar_path or sibling if needed."""
    root = root or get_project_root()
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JAR_PATH_PRERELEASE)
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
    jar = get_jar_path_from_config(root)
    if jar is None:
        return None
    s = str(jar).replace("\\", "/")
    if "pre-release" in s:
        return jar
    if "release" in s:
        from . import detection
        return detection.get_sibling_version_jar_path(jar)
    return None


def get_jadx_jar_path(root: Path) -> Path:
    """Path to the cached JADX JAR in workspace/bin/."""
    return get_bin_dir(root) / JADX_JAR_NAME


def get_jadx_url() -> str:
    """Current JADX download URL (from env or default)."""
    return os.environ.get(ENV_JADX_URL, JADX_URL)


def get_jadx_path_from_config(root: Path | None = None) -> Path | None:
    """JADX path from config or workspace/bin."""
    root = root or get_project_root()
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JADX_PATH)
    if raw:
        p = Path(raw).resolve()
        if p.is_file():
            return p
    
    #_ Fallback to workspace/bin
    local_path = get_jadx_jar_path(root)
    return local_path if local_path.is_file() else None


def get_decompiled_dir(root: Path | None = None, version: str = "release") -> Path:
    """Decompiled code directory for a version."""
    return get_workspace_dir(root) / "decompiled" / version


def get_assets_zip_path(root: Path | None = None, version: str = "release") -> Path | None:
    """Path to the Assets.zip file in the game installation."""
    jar = get_jar_path_release_from_config(root) if version == "release" else get_jar_path_prerelease_from_config(root)
    if not jar:
        return None
    # HytaleServer.jar is usually in .../Server/HytaleServer.jar
    # Assets.zip is usually in .../Assets.zip (sibling of Server/ directory)
    assets_path = jar.parent.parent / "Assets.zip"
    return assets_path if assets_path.exists() else None


def get_decompiled_raw_dir(root: Path | None = None, version: str = "release") -> Path:
    """Raw JADX directory for a version (before pruning)."""
    return get_workspace_dir(root) / "decompiled_raw" / version


def get_db_dir(root: Path | None = None) -> Path:
    """SQLite bases directory. Uses PRISM_DB_DIR if defined."""
    env_dir = os.environ.get(ENV_DB_DIR)
    if env_dir and env_dir.strip():
        return Path(env_dir.strip()).resolve()
    return get_workspace_dir(root) / "db"


def get_db_path(root: Path | None = None, version: str | None = None) -> Path:
    """Path to the DB. If version is None, uses active_server from config (default 'release')."""
    root = root or get_project_root()
    if version is None:
        cfg = load_config(root)
        active = cfg.get(CONFIG_KEY_ACTIVE_SERVER)
        if active in VALID_SERVER_VERSIONS:
            version = active
        else:
            db_dir_default = get_workspace_dir(root) / "db"
            legacy = db_dir_default / "prism_api.db"
            if legacy.exists():
                return legacy
            version = "release"
    if version == "release":
        env_path = os.environ.get(ENV_DB_PATH_RELEASE)
    else:
        env_path = os.environ.get(ENV_DB_PATH_PRERELEASE)
    if env_path and env_path.strip():
        return Path(env_path.strip()).resolve()
    db_dir = get_db_dir(root)
    return db_dir / f"prism_api_{version}.db"


def get_assets_db_path(root: Path | None = None, version: str | None = None) -> Path:
    """Path to the specific Assets DB (hybrid approach)."""
    root = root or get_project_root()
    if version is None:
        version = get_active_version(root)
    db_dir = get_db_dir(root)
    return db_dir / f"prism_assets_{version}.db"


def get_logs_dir(root: Path | None = None) -> Path:
    """Logs directory."""
    base = root if root is not None else get_project_root()
    return base / "logs"


def get_active_version(root: Path | None = None) -> str:
    """Gets the active version from the configuration, or 'release' by default."""
    cfg = load_config(root)
    active = cfg.get(CONFIG_KEY_ACTIVE_SERVER)
    if active in VALID_SERVER_VERSIONS:
        return active
    return "release"
