# API extractor from decompiled Java code (regex). Feeds SQLite + FTS5.

import re
import sys
from pathlib import Path

from tqdm import tqdm

from . import config_impl
from . import db

# Files processed between each commit to reduce transaction size and memory
BATCH_COMMIT_FILES = 1000

# Same regex as Server/Scripts/generate_api_context.py (but improved)
RE_PACKAGE = re.compile(r"package\s+([\w\.]+);")
RE_CLASS = re.compile(r"public\s+(?:abstract\s+|final\s+)?(class|interface|record|enum)\s+(\w+)")
RE_METHOD = re.compile(
    r"(@\w+\s+)?public\s+(?:abstract\s+|static\s+|final\s+|synchronized\s+|native\s+)*([\w\<\>\[\]\.]+)\s+(\w+)\s*\(([^\)]*)\)"
)


def _extract_from_java(content: str, file_path: str) -> list[tuple[str, str, str, list[dict]]]:
    """
    Extract from a Java file: package, class_name, kind and list of methods.
    Uses bracket tracking to correctly attribute methods to inner/multiple classes.
    """
    pkg_match = RE_PACKAGE.search(content)
    if not pkg_match:
        return []
    pkg = pkg_match.group(1)

    classes_found = list(RE_CLASS.finditer(content))
    if not classes_found:
        return []

    # Get all potential methods
    methods_found = list(RE_METHOD.finditer(content))
    
    # Simple bracket tracking to find scope ranges
    # We use a stack of (start_index, type, name) for classes
    class_scopes = []
    stack = []
    
    # We'll walk through the file once to find '{' and '}'
    # but we only care about those that relate to classes.
    # This is a heuristic but much better than global regex.
    
    # Optimization: pre-find the positions of all class declarations
    class_starts = {m.start(): (m.group(1), m.group(2)) for m in classes_found}
    
    # Find all braces
    brace_pos = [i for i, char in enumerate(content) if char in ('{', '}')]
    
    results_map = {} # (class_name, kind) -> methods_list

    for i in brace_pos:
        char = content[i]
        if char == '{':
            # Check if this brace belongs to a class nearby (searching backwards for a class decl)
            # A simple way is to see if any class match ends just before this brace.
            # However, since classes can have annotations/extends, we just check if
            # we are "starting" a class from our classes_found list.
            
            this_class = None
            for start_pos, info in class_starts.items():
                if start_pos < i:
                    # Check if this class is the closest preceding declaration
                    # and hasn't been "opened" yet.
                    # Simplified: if it's the next one in the sorted list.
                    pass
            
            # More robust: find which class declaration is being opened by this brace
            # We look for the class decl that ends closest to this '{'
            best_match = None
            max_end = -1
            for m in classes_found:
                if m.end() < i and m.end() > max_end:
                    # Ensure no other '{' was between m.end() and i
                    if not any(b < i and b > m.end() and content[b] == '{' for b in brace_pos):
                        best_match = m
                        max_end = m.end()
            
            if best_match:
                stack.append((best_match.group(2), best_match.group(1)))
            else:
                stack.append(None) # Not a class (method, etc)
        else: # char == '}'
            if stack:
                finished = stack.pop()
                # If it was a class, we could record it, but we can also do it simpler:
                # Just know that while 'finished' is at top of stack, we are in that class.
                pass

    # Actually, a simpler approach for a regex-based tool:
    # 1. For each class found, find its opening '{'.
    # 2. Track braces to find its closing '}'.
    # 3. Only look for methods inside those bounds.
    
    final_results = []
    
    for class_match in classes_found:
        kind = class_match.group(1)
        name = class_match.group(2)
        start_search = class_match.end()
        
        # Find first '{' after class decl
        first_brace = content.find('{', start_search)
        if first_brace == -1: continue
        
        # Track braces to find closing '}'
        depth = 1
        end_search = -1
        for i in range(first_brace + 1, len(content)):
            if content[i] == '{': depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    end_search = i
                    break
        
        if end_search == -1: end_search = len(content)
        
        # Extract methods only within [first_brace, end_search]
        class_content = content[first_brace:end_search]
        methods = []
        for m in RE_METHOD.finditer(class_content):
            # RE_METHOD groups: 1:@Annotation, 2:Returns, 3:Name, 4:Params
            m_name = m.group(3)
            if m_name == name: continue # Constructor
            
            methods.append({
                "method": m_name,
                "returns": m.group(2),
                "params": m.group(4).strip(),
                "is_static": "static" in m.group(0), # Brute force but safe with current regex
                "annotation": m.group(1).strip() if m.group(1) else None,
            })
        
        final_results.append((pkg, name, kind, methods))
        
    return final_results


def run_index(root: Path | None = None, version: str = "release") -> tuple[bool, str | tuple[int, int]]:
    """
    Walk workspace/decompiled/<version>, extract classes and methods with regex,
    and fill prism_api_<version>.db. Returns (True, (num_classes, num_methods));
    (False, "no_decompiled") if no code; (False, "db_error") if DB fails.
    """
    root = root or config_impl.get_project_root()
    decompiled_dir = config_impl.get_decompiled_dir(root, version)
    if not decompiled_dir.is_dir():
        return (False, "no_decompiled")
    java_files = list(decompiled_dir.rglob("*.java"))
    if not java_files:
        return (False, "no_decompiled")

    db_path = config_impl.get_db_path(root, version)
    try:
        with db.connection(db_path) as conn:
            db.init_schema(conn)
            db.clear_tables(conn)
            files_processed = 0
            for jpath in tqdm(java_files, unit=" files", desc="Indexing", file=sys.stderr, colour="green"):
                try:
                    content = jpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                # Relative path to decompiled directory for storage
                try:
                    rel_path = jpath.relative_to(decompiled_dir)
                except ValueError:
                    rel_path = jpath
                file_path_str = str(rel_path).replace("\\", "/")
                
                # Extract and insert
                results = _extract_from_java(content, file_path_str)
                for pkg, class_name, kind, methods in results:
                    class_id = db.insert_class(conn, pkg, class_name, kind, file_path_str)
                    for m in methods:
                        db.insert_method(
                            conn,
                            class_id,
                            m["method"],
                            m["returns"],
                            m["params"],
                            m["is_static"],
                            m["annotation"],
                        )
                        db.insert_fts_row(
                            conn,
                            pkg,
                            class_name,
                            kind,
                            m["method"],
                            m["returns"],
                            m["params"],
                        )
                files_processed += 1
                if files_processed % BATCH_COMMIT_FILES == 0:
                    conn.commit()
            conn.commit()
            stats = db.get_stats(conn)
        return (True, stats)
    except Exception as e:
        import traceback
        traceback.print_exc() # Log to stderr for the agent/user to see
        return (False, "db_error")
