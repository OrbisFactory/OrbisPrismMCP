from pathlib import Path
from typing import Any, TYPE_CHECKING
from ..infrastructure import db

if TYPE_CHECKING:
    from ..ports import ConfigProvider

def get_hierarchy(config_provider: "ConfigProvider", version: str, package: str, class_name: str, root: Path | None = None) -> dict[str, Any]:
    """
    Returns the hierarchy of a class: parents and implemented interfaces.
    """
    root = root or config_provider.get_project_root()
    db_path = config_provider.get_db_path(root, version)
    
    with db.connection(db_path) as conn:
        root_class = db.get_class_and_methods(conn, package, class_name)
        if not root_class:
            return {"error": "not_found", "message": f"Class {package}.{class_name} not found."}
        
        # We'll build the tree upwards (parents)
        parents = []
        current = root_class
        visited = { (package, class_name) }
        
        while current and current.get("parent"):
            parent_fqcn = current["parent"]
            # Parent is just "ClassName" or "package.ClassName" or "ClassName<Generics>"
            # Our extractor already cleaned Generics.
            
            # Find parent in DB
            parent_info = _find_class_by_name_or_fqcn(conn, parent_fqcn, current["package"])
            if parent_info:
                if (parent_info["package"], parent_info["class_name"]) in visited:
                    break # Loop detected
                visited.add((parent_info["package"], parent_info["class_name"]))
                parents.append({
                    "package": parent_info["package"],
                    "class_name": parent_info["class_name"],
                    "kind": parent_info["kind"]
                })
                current = parent_info
            else:
                # Still add it as external
                parents.append({"class_name": parent_fqcn, "external": True})
                current = None # Stop search
        
        return {
            "class_name": class_name,
            "package": package,
            "kind": root_class["kind"],
            "parent_tree": parents,
            "interfaces": root_class.get("interfaces", "").split(",") if root_class.get("interfaces") else []
        }

def _find_class_by_name_or_fqcn(conn, name_ref, current_package):
    if "." in name_ref:
        parts = name_ref.rsplit(".", 1)
        return db.get_class_and_methods(conn, parts[0], parts[1])
    else:
        # Search in same package
        res = db.get_class_and_methods(conn, current_package, name_ref)
        if res: return res
        
        # Search globally if unique
        rows = db.search_fts(conn, name_ref, limit=2)
        if len(rows) == 1 or (len(rows) > 1 and all(r["class_name"] == name_ref for r in rows)):
             # Heuristic: if only one class with that name exists, it's likely that one
             return db.get_class_and_methods(conn, rows[0]["package"], rows[0]["class_name"])
    return None
