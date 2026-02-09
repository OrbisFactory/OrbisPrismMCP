# src/prism/infrastructure/extractor.py
#? Extractor de API desde código Java decompilado (regex). Alimenta SQLite + FTS5.

import re
import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from . import config_impl
from . import db

#_ Archivos procesados entre cada commit para reducir el tamaño de la transacción y la memoria
BATCH_COMMIT_FILES = 1000

#_ Misma regex que Server/Scripts/generate_api_context.py (pero mejorada)
RE_PACKAGE = re.compile(r"package\s+([\w\.]+);")
RE_CLASS = re.compile(
    r"public\s+(?:abstract\s+|final\s+)?(class|interface|record|enum)\s+(\w+)"
    r"(?:\s+extends\s+([\w\<\>\.,\s]+?))?"
    r"(?:\s+implements\s+([\w\<\>\.,\s]+?))?"
    r"\s*\{"
)
RE_METHOD = re.compile(
    r"(@\w+\s+)?public\s+(?:abstract\s+|static\s+|final\s+|synchronized\s+|native\s+)*([\w\<\>\[\]\.]+)\s+(\w+)\s*\(([^\)]*)\)"
)
RE_CONSTANT = re.compile(
    r"public\s+static\s+final\s+([\w\<\>\[\]\.]+)\s+(\w+)\s*=\s*(.*?);"
)


def _extract_from_java(content: str, file_path: str) -> list[tuple[str, str, str, list[dict], str | None, str | None, list[dict]]]:
    """
    Extrae de un archivo Java: package, class_name, kind, methods, parent, interfaces, y constants.
    Usa seguimiento de llaves para atribuir correctamente los elementos a clases internas/múltiples.
    """
    pkg_match = RE_PACKAGE.search(content)
    if not pkg_match:
        return []
    pkg = pkg_match.group(1)

    classes_found = list(RE_CLASS.finditer(content))
    if not classes_found:
        return []

    final_results = []
    
    for class_match in classes_found:
        kind = class_match.group(1)
        name = class_match.group(2)
        parent = class_match.group(3).strip() if class_match.group(3) else None
        interfaces = class_match.group(4).strip() if class_match.group(4) else None
        
        #_ Limpia genéricos de parent/interfaces para una mejor indexación/enlace
        if parent: parent = re.sub(r"\<.*?\>", "", parent).strip()
        if interfaces: interfaces = re.sub(r"\<.*?\>", "", interfaces).strip()

        start_search = class_match.end()
        
        #_ Encuentra la primera '{' (que en realidad es parte de la coincidencia RE_CLASS, pero seamos cuidadosos)
        #_ En realidad RE_CLASS termina en '{', así que start_search está justo después de '{'
        first_brace = class_match.end() - 1 #_ Posición de '{'
        
        #_ Sigue las llaves para encontrar la '}' de cierre
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
        
        #_ Extrae elementos solo dentro de [first_brace, end_search]
        class_content = content[first_brace:end_search]
        
        #_ Métodos
        methods = []
        for m in RE_METHOD.finditer(class_content):
            #_ Grupos RE_METHOD: 1:@Annotation, 2:Returns, 3:Name, 4:Params
            m_name = m.group(3)
            if m_name == name: continue #_ Constructor
            
            methods.append({
                "method": m_name,
                "returns": m.group(2),
                "params": m.group(4).strip(),
                "is_static": "static" in m.group(0),
                "annotation": m.group(1).strip() if m.group(1) else None,
            })
        
        #_ Constantes
        constants = []
        for c in RE_CONSTANT.finditer(class_content):
            #_ Grupos RE_CONSTANT: 1:Type, 2:Name, 3:Value
            constants.append({
                "name": c.group(2),
                "type": c.group(1),
                "value": c.group(3).strip().strip('"'),
            })
        
        final_results.append((pkg, name, kind, methods, parent, interfaces, constants))
        
    return final_results


def run_index(root: Path | None = None, version: str = "release") -> tuple[bool, str | tuple[int, int, int]]:
    """
    Recorre workspace/decompiled/<version>, extrae clases, métodos y constantes con regex,
    y llena prism_api_<version>.db. Retorna (True, (num_classes, num_methods, num_constants));
    (False, "no_decompiled") si no hay código; (False, "db_error") si la DB falla.
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
        with db.connection(db_path) as conn, Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            db.init_schema(conn)
            db.clear_tables(conn)
            files_processed = 0
            
            task = progress.add_task(f"[green]Indexando {version}", total=len(java_files))

            for jpath in java_files:
                try:
                    content = jpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    progress.update(task, advance=1)
                    continue
                #_ Ruta relativa al directorio decompilado para almacenamiento
                try:
                    rel_path = jpath.relative_to(decompiled_dir)
                except ValueError:
                    rel_path = jpath
                file_path_str = str(rel_path).replace("\\", "/")
                
                #_ Extraer e insertar
                results = _extract_from_java(content, file_path_str)
                for pkg, class_name, kind, methods, parent, interfaces, constants in results:
                    class_id = db.insert_class(conn, pkg, class_name, kind, file_path_str, parent, interfaces)
                    
                    #_ Insertar métodos
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
                            method_name=m["method"],
                            returns=m["returns"],
                            params=m["params"],
                        )
                    
                    #_ Insertar constantes
                    for c in constants:
                        db.insert_constant(
                            conn,
                            class_id,
                            c["name"],
                            c["type"],
                            c["value"],
                        )
                        db.insert_fts_row(
                            conn,
                            pkg,
                            class_name,
                            kind,
                            const_name=c["name"],
                            const_value=c["value"],
                        )
                
                files_processed += 1
                if files_processed % BATCH_COMMIT_FILES == 0:
                    conn.commit()
                
                progress.update(task, advance=1)

            conn.commit()
            stats = db.get_stats(conn)
        return (True, stats)
    except Exception as e:
        import traceback
        traceback.print_exc() #_ Log a stderr para que el agente/usuario lo vea
        return (False, "db_error")