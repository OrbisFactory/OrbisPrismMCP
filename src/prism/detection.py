# HytaleServer.jar detection: env, standard Windows paths and validation.

import os
import shutil
import zipfile
from pathlib import Path

from . import config


def is_valid_jar(path: Path) -> bool:
    """Check that the file exists and is a valid JAR (public, for CLI use)."""
    return _is_valid_jar(path)


def _is_valid_jar(path: Path) -> bool:
    """Check that the file exists and is a JAR (ZIP with valid structure)."""
    if not path.is_file() or path.suffix.lower() != ".jar":
        return False
    try:
        with zipfile.ZipFile(path, "r") as z:
            # A JAR has at least META-INF/MANIFEST.MF or classes
            names = z.namelist()
            return any(
                n.startswith("META-INF/") or n.endswith(".class")
                for n in names[:50]
            )
    except (zipfile.BadZipFile, OSError):
        return False


# Subpath under Hytale root to reach server JAR (release or pre-release)
_RELATIVE_SERVER_JAR = ("install", "release", "package", "game", "latest", "Server", config.HYTALE_JAR_NAME)
_RELATIVE_SERVER_JAR_PRERELEASE = ("install", "pre-release", "package", "game", "latest", "Server", config.HYTALE_JAR_NAME)


def find_jar_paths_from_hytale_root(hytale_root: Path) -> tuple[Path | None, Path | None]:
    """
    Given the Hytale root path (e.g. %APPDATA%\\Hytale), infer and validate
    HytaleServer.jar paths for release and pre-release.
    Returns (release_jar, prerelease_jar); each is None if not found or invalid.
    """
    root = hytale_root.resolve()
    if not root.is_dir():
        return (None, None)
    release_jar = root.joinpath(*_RELATIVE_SERVER_JAR)
    prerelease_jar = root.joinpath(*_RELATIVE_SERVER_JAR_PRERELEASE)
    r = release_jar if release_jar.is_file() and _is_valid_jar(release_jar) else None
    p = prerelease_jar if prerelease_jar.is_file() and _is_valid_jar(prerelease_jar) else None
    return (r, p)


def is_hytale_root(path: Path) -> bool:
    """Check whether the path is the Hytale root folder (contains install/release or install/pre-release)."""
    root = path.resolve()
    if not root.is_dir():
        return False
    release_jar = root.joinpath(*_RELATIVE_SERVER_JAR)
    prerelease_jar = root.joinpath(*_RELATIVE_SERVER_JAR_PRERELEASE)
    return release_jar.is_file() or prerelease_jar.is_file()


def _search_standard_paths() -> list[Path]:
    """Standard paths: Hytale root (%APPDATA%\\Hytale) and Server release."""
    candidates: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        hytale_root = Path(appdata) / "Hytale"
        if hytale_root.is_dir():
            candidates.append(hytale_root)
        server_install = hytale_root / "install" / "release" / "package" / "game" / "latest" / "Server"
        if server_install.is_dir() and server_install not in candidates:
            candidates.append(server_install)
    return candidates


def get_sibling_version_jar_path(jar_path: Path) -> Path | None:
    """
    If the JAR path contains the segment 'install/release/...' or 'install/pre-release/...',
    build the "sibling" path (release <-> pre-release) and return it if it exists
    and is a valid JAR. Otherwise return None.
    """
    resolved = jar_path.resolve()
    parts = list(resolved.parts)
    try:
        i_install = parts.index("install")
    except ValueError:
        return None
    if i_install + 1 >= len(parts):
        return None
    version_segment = parts[i_install + 1]
    if version_segment == "release":
        sibling_parts = parts[: i_install + 1] + ["pre-release"] + parts[i_install + 2 :]
    elif version_segment == "pre-release":
        sibling_parts = parts[: i_install + 1] + ["release"] + parts[i_install + 2 :]
    else:
        return None
    sibling = Path(*sibling_parts)
    if sibling.is_file() and _is_valid_jar(sibling):
        return sibling
    return None


def find_jar_in_dir(directory: Path, jar_name: str = config.HYTALE_JAR_NAME) -> Path | None:
    """Search for the JAR in a directory (and one level of subfolders)."""
    if not directory.is_dir():
        return None
    # Directly in the folder
    direct = directory / jar_name
    if direct.is_file():
        return direct
    for child in directory.iterdir():
        if child.is_dir():
            candidate = child / jar_name
            if candidate.is_file():
                return candidate
    return None


def resolve_jadx_path(root: Path | None = None) -> str | None:
    """
    Resolve the JADX executable path for saving to config.
    Order: JADX_PATH -> bin/jadx or bin/jadx.bat in root -> which('jadx').
    Returns the path as string or None if not found.
    """
    root = root or config.get_project_root()

    def _check_path(p: Path) -> str | None:
        if p.is_file():
            return str(p.resolve())
        if p.is_dir():
            for name in ("jadx", "jadx.bat", "jadx.cmd"):
                candidate = p / name
                if candidate.is_file():
                    return str(candidate.resolve())
        return None

    # 1. Environment variable
    env_path = os.environ.get(config.ENV_JADX_PATH)
    if env_path:
        result = _check_path(Path(env_path).resolve())
        if result:
            return result
    # 2. bin/ in project root
    bin_dir = root / "bin"
    if bin_dir.is_dir():
        for name in ("jadx", "jadx.bat", "jadx.cmd"):
            candidate = bin_dir / name
            if candidate.is_file():
                return str(candidate.resolve())
    # 3. which('jadx')
    jadx = shutil.which("jadx")
    if jadx:
        return jadx
    return None


def find_and_validate_jar(root: Path | None = None) -> Path | None:
    """
    Infer HytaleServer.jar path:
    1. HYTALE_JAR_PATH env var
    2. Saved config (jar_path; see prism config set game_path)
    3. Standard Windows path: %APPDATA%\\Hytale\\install\\...\\Server
    Returns valid JAR Path or None.
    """
    root = root or config.get_project_root()
    jar_name = config.HYTALE_JAR_NAME

    # 1. Environment variable (may be JAR or Hytale root folder)
    env_path = os.environ.get(config.ENV_JAR_PATH)
    if env_path:
        p = Path(env_path).resolve()
        if p.is_dir() and is_hytale_root(p):
            release_jar, prerelease_jar = find_jar_paths_from_hytale_root(p)
            if release_jar:
                return release_jar
            if prerelease_jar:
                return prerelease_jar
        elif _is_valid_jar(p):
            return p

    # 2. Saved config
    from .config import get_jar_path_from_config
    saved = get_jar_path_from_config(root)
    if saved and _is_valid_jar(saved):
        return saved

    # 3. Standard paths (Hytale root or Server folder)
    for candidate_dir in _search_standard_paths():
        if is_hytale_root(candidate_dir):
            release_jar, prerelease_jar = find_jar_paths_from_hytale_root(candidate_dir)
            if release_jar:
                return release_jar
            if prerelease_jar:
                return prerelease_jar
        else:
            found = find_jar_in_dir(candidate_dir, jar_name)
            if found and _is_valid_jar(found):
                return found

    return None
