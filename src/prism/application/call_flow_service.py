# src/prism/application/call_flow_service.py
from pathlib import Path
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from ..ports import ConfigProvider, IndexRepository


def get_call_flow(
    config_provider: "ConfigProvider",
    index_repository: "IndexRepository",
    root: Path | None,
    version: str,
    target_class: str,
    method_name: str,
    limit: int = 100,
) -> tuple[dict | None, dict | None]:
    """
    Analyzes who calls target_class.method_name.
    Groups results by package and class for easier reading.
    """
    from ..domain.constants import normalize_version
    from .usages import find_usages

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    
    #_ Search for usages in source code
    usages, err = find_usages(config_provider, root, version, f"{target_class}.{method_name}", limit=limit)
    if err:
        return None, err
    
    #_ Group results
    flow = defaultdict(lambda: defaultdict(list))
    for u in usages:
        path = u.get("file_path", "unknown")
        #_ Try to infer package and class from file_path (e.g. com/hypixel/Class.java)
        pkg = "unknown"
        cls = "unknown"
        if path.endswith(".java"):
            parts = path[:-5].split("/")
            if len(parts) > 1:
                pkg = ".".join(parts[:-1])
                cls = parts[-1]
            else:
                cls = parts[0]

        flow[pkg][cls].append({
            "file_path": path,
            "line": u.get("line"),
            "line_content": u.get("content")
        })
    
    #_ Convert to a serializable format
    results = []
    for pkg in sorted(flow.keys()):
        pkg_data = {"package": pkg, "classes": []}
        for cls in sorted(flow[pkg].keys()):
            pkg_data["classes"].append({
                "class_name": cls,
                "calls": flow[pkg][cls]
            })
        results.append(pkg_data)
        
    return {
        "version": version,
        "target": f"{target_class}.{method_name}",
        "total_usages": len(usages),
        "flow": results
    }, None
