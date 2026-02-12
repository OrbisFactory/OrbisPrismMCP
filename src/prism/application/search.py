# Use case: FTS search on the index.

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ports import ConfigProvider, IndexRepository


def sanitize_fts_query(query: str) -> str:
    """
    Sanitizes the query for FTS5. 
    1. Wrap terms containing dots in double quotes to avoid syntax errors.
    2. If a term looks like a FQCN (e.g. com.pkg.Class), try to search across package and class_name columns.
    """
    if not query:
        return ""
    
    import re
    #_ Split by whitespace but keep quoted phrases together
    parts = re.findall(r'(?:"[^"]*"|\S+)', query)
    sanitized_parts = []
    
    for part in parts:
        #_ If it's already quoted, keep as is
        if part.startswith('"') and part.endswith('"'):
            sanitized_parts.append(part)
            continue
            
        #_ If it contains a dot, it might be a FQCN
        if "." in part:
            #_ Special case: if it ends with .*, it's a prefix search for package
            if part.endswith(".*"):
                sanitized_parts.append(f'package:"{part[:-2]}*"')
                continue
                
            #_ Heuristic for FQCN: last part is usually the class name (starts with uppercase)
            subparts = part.split(".")
            if len(subparts) > 1:
                last_part = subparts[-1]
                pkg_part = ".".join(subparts[:-1])
                
                #_ If last part starts with uppercase, it's likely Package.Class
                if last_part and last_part[0].isupper():
                    #_ Search for package EQUALS pkg_part AND class_name STARTS WITH last_part
                    sanitized_parts.append(f'(package:"{pkg_part}" AND class_name:"{last_part}*")')
                else:
                    #_ Just a package path or lowercase class? Search both or just quote it.
                    sanitized_parts.append(f'"{part}"')
            else:
                sanitized_parts.append(f'"{part}"')
        else:
            sanitized_parts.append(part)
            
    return " ".join(sanitized_parts)


def search_api(
    config_provider: "ConfigProvider",
    index_repository: "IndexRepository",
    root: Path | None,
    version: str,
    query: str,
    limit: int = 50,
    package_prefix: str | None = None,
    kind: str | None = None,
    unique_classes: bool = False,
    t: callable = None,
) -> tuple[list[dict], dict | None]:
    """
    Run FTS5 search. Returns (results, None) on success or ([], error_dict) on failure.
    t: optional i18n translate function for error messages.
    """
    from ..domain.constants import normalize_version

    root = root or config_provider.get_project_root()
    version = normalize_version(version)
    
    #_ Sanitize query to support dots in package names (FQCN)
    term = sanitize_fts_query(query).strip()
    
    limit = max(1, min(limit, 500))
    db_path = config_provider.get_db_path(root, version)
    if not db_path.is_file():
        msg = f"Database for version {version} does not exist. Run prism index first."
        if t:
            msg = t("cli.query.no_db", version=version)
        return ([], {"error": "no_db", "message": msg})
    try:
        results = index_repository.search(
            db_path, term, limit=limit, package_prefix=package_prefix, kind=kind, unique_classes=unique_classes
        )
        return (list(results), None)
    except sqlite3.OperationalError as e:
        err_msg = str(e).lower()
        if "fts5" in err_msg or "syntax" in err_msg:
            hint = t("cli.query.fts5_help") if t else "Use a single word or quoted phrase. Multiple terms: term1 AND term2."
            return ([], {"error": "fts5_syntax", "message": str(e), "hint": hint})
        return ([], {"error": "db", "message": str(e)})
    except Exception as e:
        return ([], {"error": "db", "message": str(e)})
