# Shared domain constants (server versions).

VALID_SERVER_VERSIONS = ("release", "prerelease")


def normalize_version(version: str | None) -> str:
    """
    Returns 'release' or 'prerelease'. If version is None or invalid, returns 'release'.
    """
    if not version or not str(version).strip():
        return "release"
    v = str(version).strip().lower()
    return v if v in VALID_SERVER_VERSIONS else "release"
