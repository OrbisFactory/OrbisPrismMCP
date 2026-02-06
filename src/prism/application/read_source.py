# Use case: read decompiled Java source file (with optional line range).

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider


def read_source(
    config_provider: "ConfigProvider",
    root: Path | None,
    version: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    """
    Read decompiled file content. Returns dict with content, file_path, version;
    if start_line/end_line given, adds total_lines, start_line, end_line and slices content.
    On error returns dict with "error" and "message".
    """
    from ..domain.constants import normalize_version

    version = normalize_version(version)
    path_str = (file_path or "").strip().replace("\\", "/").lstrip("/")
    if not path_str:
        return {"error": "missing_path", "message": "file_path is required"}
    root = root or config_provider.get_project_root()
    decompiled_dir = config_provider.get_decompiled_dir(root, version).resolve()
    full_path = (decompiled_dir / path_str).resolve()
    if not full_path.is_relative_to(decompiled_dir):
        return {"error": "invalid_path", "message": "file_path must be inside decompiled directory"}
    if not full_path.is_file():
        return {"error": "not_found", "message": f"File not found: {path_str}"}
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": "read_error", "message": str(e)}
    lines = content.splitlines()
    total_lines = len(lines)
    payload = {"content": content, "file_path": path_str, "version": version}
    if start_line is not None or end_line is not None:
        one = max(1, int(start_line) if start_line is not None else 1)
        two = min(total_lines, int(end_line) if end_line is not None else total_lines)
        if one > two:
            one, two = two, one
        payload["total_lines"] = total_lines
        payload["start_line"] = one
        payload["end_line"] = two
        payload["content"] = "\n".join(lines[one - 1 : two])
    return payload
