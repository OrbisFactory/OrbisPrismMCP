# Use case: find usages of a class in the decompiled source code.

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider


def find_usages(
    config_provider: "ConfigProvider",
    root: Path | None,
    version: str,
    target_class: str,
    limit: int = 100,
) -> tuple[list[dict], dict | None]:
    """
    Search for usages of a class name in the decompiled Java source.
    Returns (results, None) or ([], error_dict).
    """
    from ..domain.constants import normalize_version

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    source_dir = config_provider.get_decompiled_dir(root, version)

    if not source_dir.is_dir():
        return ([], {"error": "no_source", "message": f"Source directory for {version} not found."})

    # We look for the class name. If it's a FQCN, we can try to be more specific.
    # But often people use simple names after import.
    # For now, let's do a simple word search.
    search_term = target_class
    if "." in target_class:
        search_term = target_class.split(".")[-1]

    results = []
    try:
        # Use findstr on Windows or grep/rg if available. 
        # Since we are in a Python environment, walking files might be safer but slower.
        # Let's try to use ripgrep if available, fallback to manual walk.
        
        # Simple implementation using python walking for maximum compatibility
        count = 0
        for path in source_dir.rglob("*.java"):
            if count >= limit:
                break
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                # Look for the term as a whole word
                # If target_class is FQCN, also check for it
                pattern = r"\b" + re.escape(search_term) + r"\b"
                if target_class != search_term:
                     pattern = r"\b" + re.escape(target_class) + r"\b|\b" + re.escape(search_term) + r"\b"
                
                matches = list(re.finditer(pattern, content))
                if matches:
                    rel_path = str(path.relative_to(source_dir)).replace("\\", "/")
                    # Extract lines for context
                    lines = content.splitlines()
                    for m in matches:
                        line_no = content.count("\n", 0, m.start()) + 1
                        results.append({
                            "file_path": rel_path,
                            "line": line_no,
                            "content": lines[line_no - 1].strip()
                        })
                        count += 1
                        if count >= limit:
                            break
            except Exception:
                continue

        return (results, None)

    except Exception as e:
        return ([], {"error": "search_failed", "message": str(e)})
