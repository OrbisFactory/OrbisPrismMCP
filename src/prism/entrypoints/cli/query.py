# query command: FTS5 search in the DB.

import json
import sys
from pathlib import Path
import argparse

from ...application import search
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl
from . import out #!NUEVA_IMPORTACION


def cmd_query(
    root: Path | None = None,
    query_term: str = "",
    version: str = "release",
    limit: int = 30,
    output_json: bool = False,
) -> int:
    """Executes FTS5 search in the DB for the given version. output_json: only prints JSON."""
    root = root or config_impl.get_project_root()
    if not query_term or not query_term.strip():
        out.error(i18n.t("cli.query.usage"))
        return 1
    if version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    
    #_ Muestra un spinner durante la búsqueda
    with out.status(i18n.t("cli.query.searching", term=query_term, version=version)):
        results, err = search.search_api(root, version, query_term.strip(), limit=limit)

    if err is not None:
        out.error(err["message"])
        if err.get("hint"):
            out.error(err["hint"])
        return 1
        
    if output_json:
        #_ Para la salida JSON, mantenemos el formato original
        json_output = {"version": version, "term": query_term.strip(), "count": len(results), "results": results}
        print(json.dumps(json_output, ensure_ascii=False))
        return 0

    if not results:
        out.success(i18n.t("cli.query.no_results", term=query_term, version=version))
        return 0

    #_ Muestra los resultados en una tabla
    out.phase(i18n.t("cli.query.result_count", count=len(results), term=query_term, version=version))
    
    #_ Define las columnas que queremos mostrar y en qué orden
    columns = ["package", "class_name", "kind", "method_name", "params", "returns"]
    out.table(
        title=i18n.t("cli.query.table_title"),
        data=results,
        columns=columns
    )
    
    return 0


def run_query(args: argparse.Namespace, root: Path) -> int:
    """Dispatch of the query command."""
    if not args.term:
        out.error(i18n.t("cli.query.usage"))
        return 1
    return cmd_query(root, query_term=args.term, version=args.version, limit=args.limit, output_json=args.json)
