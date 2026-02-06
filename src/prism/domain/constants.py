# Constantes de dominio compartidas (versiones de servidor).

VALID_SERVER_VERSIONS = ("release", "prerelease")


def normalize_version(version: str | None) -> str:
    """
    Devuelve 'release' o 'prerelease'. Si version es None o no válida, devuelve 'release'.
    """
    if not version or not str(version).strip():
        return "release"
    v = str(version).strip().lower()
    return v if v in VALID_SERVER_VERSIONS else "release"
