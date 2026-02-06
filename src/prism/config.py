# Central config: default paths, constants and environment variable reading.

import os
import json
from pathlib import Path

# Hytale server JAR filename
HYTALE_JAR_NAME = "HytaleServer.jar"

# Core package kept after pruning
CORE_PACKAGE = "com.hypixel.hytale"
CORE_PACKAGE_PATH = "com/hypixel/hytale"

# Environment variables (BluePrint / convention)
ENV_JAR_PATH = "HYTALE_JAR_PATH"
ENV_OUTPUT_DIR = "PRISM_OUTPUT_DIR"
ENV_JADX_PATH = "JADX_PATH"
ENV_LANG = "PRISM_LANG"
# Project root when launched from MCP/Docker (avoids relying only on cwd)
ENV_WORKSPACE = "PRISM_WORKSPACE"
# Decoupled DB path: directory where DBs live or exact path per version (volume/read-only)
ENV_DB_DIR = "PRISM_DB_DIR"
ENV_DB_PATH_RELEASE = "PRISM_DB_PATH_RELEASE"
ENV_DB_PATH_PRERELEASE = "PRISM_DB_PATH_PRERELEASE"

# Config file names (project root)
CONFIG_FILENAME = ".prism.json"
CONFIG_KEY_JAR_PATH = "jar_path"
CONFIG_KEY_JAR_PATH_PRERELEASE = "jar_path_prerelease"
CONFIG_KEY_JAR_PATH_RELEASE = "jar_path_release"
CONFIG_KEY_OUTPUT_DIR = "output_dir"
CONFIG_KEY_JADX_PATH = "jadx_path"
CONFIG_KEY_LANG = "lang"
CONFIG_KEY_ACTIVE_SERVER = "active_server"

# Supported server versions (each has its own DB and decompiled folder)
VALID_SERVER_VERSIONS = ("release", "prerelease")


def get_project_root() -> Path:
    """Project root: folder containing main.py / .prism.json (or src)."""
    env_root = os.environ.get(ENV_WORKSPACE)
    if env_root:
        p = Path(env_root).resolve()
        if p.is_dir():
            return p
    # If we are in src/prism/, go up two levels
    current = Path(__file__).resolve().parent
    if (current / ".." / ".." / "main.py").resolve().exists():
        return (current / ".." / "..").resolve()
    # Fallback: current working directory
    return Path.cwd()


def get_workspace_dir(root: Path | None = None) -> Path:
    """Workspace directory (decompiled, db, server)."""
    root = root or get_project_root()
    env_dir = os.environ.get(ENV_OUTPUT_DIR)
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    return root / "workspace"


def get_config_path(root: Path | None = None) -> Path:
    """Path to the persistent config file."""
    root = root or get_project_root()
    return root / CONFIG_FILENAME


def load_config(root: Path | None = None) -> dict:
    """Load config from .prism.json. Returns empty dict if it does not exist."""
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
    """Get JAR path from config (stored string). None if not set."""
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JAR_PATH)
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def get_jar_path_release_from_config(root: Path | None = None) -> Path | None:
    """Release version JAR. Reads jar_path_release or infers from jar_path / sibling."""
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
    # Single JAR without release/prerelease path: treat as release
    return jar


def get_jar_path_prerelease_from_config(root: Path | None = None) -> Path | None:
    """Prerelease version JAR. Reads jar_path_prerelease or infers from jar_path / sibling."""
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


def get_jadx_path_from_config(root: Path | None = None) -> Path | None:
    """Get JADX path from config. None if not set or not executable."""
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JADX_PATH)
    if not raw:
        return None
    p = Path(raw).resolve()
    return p if p.is_file() else None


def get_decompiled_dir(root: Path | None = None, version: str = "release") -> Path:
    """Decompiled output directory for a version (release/prerelease)."""
    return get_workspace_dir(root) / "decompiled" / version


def get_decompiled_raw_dir(root: Path | None = None, version: str = "release") -> Path:
    """Raw JADX output directory for a version (before pruning)."""
    return get_workspace_dir(root) / "decompiled_raw" / version


def get_db_dir(root: Path | None = None) -> Path:
    """SQLite database directory. If PRISM_DB_DIR is set, use that path."""
    env_dir = os.environ.get(ENV_DB_DIR)
    if env_dir and env_dir.strip():
        return Path(env_dir.strip()).resolve()
    return get_workspace_dir(root) / "db"


def get_db_path(root: Path | None = None, version: str | None = None) -> Path:
    """
    DB path. If version is None, use active_server from config (default 'release').
    Compatibility: if no active_server and prism_api.db exists, return that.
    If PRISM_DB_PATH_RELEASE/PRISM_DB_PATH_PRERELEASE are set, use that path for that version.
    If PRISM_DB_DIR is set, DBs are in that directory with name prism_api_{version}.db.
    This allows pointing to a volume or read-only DB.
    """
    root = root or get_project_root()
    # Resolve effective version if not passed
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
    # Override by exact path for that version
    if version == "release":
        env_path = os.environ.get(ENV_DB_PATH_RELEASE)
    else:
        env_path = os.environ.get(ENV_DB_PATH_PRERELEASE)
    if env_path and env_path.strip():
        return Path(env_path.strip()).resolve()
    # Override by common directory (same file name)
    db_dir = get_db_dir(root)
    return db_dir / f"prism_api_{version}.db"


def get_logs_dir(root: Path | None = None) -> Path:
    """Logs directory."""
    base = root if root is not None else get_project_root()
    return base / "logs"
