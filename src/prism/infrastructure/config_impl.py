# Configuración central: paths por defecto, constantes y variables de entorno.

import json
import os
from pathlib import Path

from ..domain.constants import VALID_SERVER_VERSIONS

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
ENV_WORKSPACE = "PRISM_WORKSPACE"
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


def get_project_root() -> Path:
    """Raíz del proyecto: carpeta que contiene main.py / .prism.json."""
    env_root = os.environ.get(ENV_WORKSPACE)
    if env_root:
        p = Path(env_root).resolve()
        if p.is_dir():
            return p
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "main.py").exists():
            return current.resolve()
        current = current.parent
    return Path.cwd()


def get_workspace_dir(root: Path | None = None) -> Path:
    """Directorio workspace (decompiled, db, server)."""
    root = root or get_project_root()
    env_dir = os.environ.get(ENV_OUTPUT_DIR)
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    return root / "workspace"


def get_config_path(root: Path | None = None) -> Path:
    """Ruta al archivo de configuración persistente."""
    root = root or get_project_root()
    return root / CONFIG_FILENAME


def load_config(root: Path | None = None) -> dict:
    """Carga config desde .prism.json. Devuelve dict vacío si no existe."""
    path = get_config_path(root)
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict, root: Path | None = None) -> None:
    """Guarda config en .prism.json."""
    path = get_config_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_jar_path_from_config(root: Path | None = None) -> Path | None:
    """Obtiene ruta JAR desde config. None si no está definida."""
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JAR_PATH)
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def get_jar_path_release_from_config(root: Path | None = None) -> Path | None:
    """JAR de versión release. Infiere desde jar_path o sibling si hace falta."""
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
    """JAR de versión prerelease. Infiere desde jar_path o sibling si hace falta."""
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
    """Ruta a JADX desde config. None si no está o no es ejecutable."""
    cfg = load_config(root)
    raw = cfg.get(CONFIG_KEY_JADX_PATH)
    if not raw:
        return None
    p = Path(raw).resolve()
    return p if p.is_file() else None


def get_decompiled_dir(root: Path | None = None, version: str = "release") -> Path:
    """Directorio de código descompilado para una versión."""
    return get_workspace_dir(root) / "decompiled" / version


def get_decompiled_raw_dir(root: Path | None = None, version: str = "release") -> Path:
    """Directorio raw de JADX para una versión (antes del prune)."""
    return get_workspace_dir(root) / "decompiled_raw" / version


def get_db_dir(root: Path | None = None) -> Path:
    """Directorio de bases SQLite. Si PRISM_DB_DIR está definido, se usa ese."""
    env_dir = os.environ.get(ENV_DB_DIR)
    if env_dir and env_dir.strip():
        return Path(env_dir.strip()).resolve()
    return get_workspace_dir(root) / "db"


def get_db_path(root: Path | None = None, version: str | None = None) -> Path:
    """Ruta a la DB. Si version es None, usa active_server de config (por defecto 'release')."""
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


def get_logs_dir(root: Path | None = None) -> Path:
    """Directorio de logs."""
    base = root if root is not None else get_project_root()
    return base / "logs"
