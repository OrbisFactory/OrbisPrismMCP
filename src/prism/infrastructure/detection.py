# Detection of HytaleServer.jar: environment variables, standard Windows paths, and validation.

import os
import shutil
import zipfile
from pathlib import Path

from . import config_impl


def is_valid_jar(path: Path) -> bool:
    """Checks that the file exists and is a valid JAR (public, for CLI)."""
    return _is_valid_jar(path)


def _is_valid_jar(path: Path) -> bool:
    """Checks that the file exists and is a JAR (ZIP with valid structure)."""
    if not path.is_file() or path.suffix.lower() != ".jar":
        return False
    try:
        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            return any(
                n.startswith("META-INF/") or n.endswith(".class")
                for n in names[:50]
            )
    except (zipfile.BadZipFile, OSError):
        return False


_RELATIVE_SERVER_JAR = ("install", "release", "package", "game", "latest", "Server", config_impl.HYTALE_JAR_NAME)
_RELATIVE_SERVER_JAR_PRERELEASE = ("install", "pre-release", "package", "game", "latest", "Server", config_impl.HYTALE_JAR_NAME)


def find_jar_paths_from_hytale_root(hytale_root: Path) -> tuple[Path | None, Path | None]:
    """Given the Hytale root (e.g. %APPDATA%\\Hytale), infers and validates HytaleServer.jar paths."""
    root = hytale_root.resolve()
    if not root.is_dir():
        return (None, None)
    release_jar = root.joinpath(*_RELATIVE_SERVER_JAR)
    prerelease_jar = root.joinpath(*_RELATIVE_SERVER_JAR_PRERELEASE)
    r = release_jar if release_jar.is_file() and _is_valid_jar(release_jar) else None
    p = prerelease_jar if prerelease_jar.is_file() and _is_valid_jar(prerelease_jar) else None
    return (r, p)


def is_hytale_root(path: Path) -> bool:
    """Checks if the path is the Hytale root folder."""
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
    """If the JAR path contains 'install/release/...' or 'install/pre-release/...', constructs the sibling path."""
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


def find_jar_in_dir(directory: Path, jar_name: str = config_impl.HYTALE_JAR_NAME) -> Path | None:
    """Searches for the JAR in a directory (and one level of subfolders)."""
    if not directory.is_dir():
        return None
    direct = directory / jar_name
    if direct.is_file():
        return direct
    for child in directory.iterdir():
        if child.is_dir():
            candidate = child / jar_name
            if candidate.is_file():
                return candidate
    return None




def find_and_validate_jar(root: Path | None = None) -> Path | None:
    """Infers the path to HytaleServer.jar: environment variables, config, standard Windows path."""
    root = root or config_impl.get_project_root()
    jar_name = config_impl.HYTALE_JAR_NAME

    env_path = os.environ.get(config_impl.ENV_JAR_PATH)
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

    saved = config_impl.get_jar_path_from_config(root)
    if saved and _is_valid_jar(saved):
        return saved

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
