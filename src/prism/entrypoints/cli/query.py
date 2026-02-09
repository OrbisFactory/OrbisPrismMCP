# src/prism/entrypoints/cli/query.py
#? Comando 'query' para búsqueda FTS5 en la DB, con Typer.

import json
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ...application import search
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl
from . import out

#_ Creamos una sub-aplicación de Typer para el comando 'query'
app = typer.Typer(help=i18n.t("cli.query.help"))

@app.command(name="search")
def query_cmd(
    ctx: typer.Context,
    term: Annotated[str, typer.Argument(help="Término de búsqueda (regex estilo Rust por defecto, usa \\b para límites de palabra).")] = "",
    version: Annotated[Optional[str], typer.Argument(help="Versión a consultar (release, prerelease).", 
                                                choices=list(VALID_SERVER_VERSIONS))] = "release",
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Mostrar resultados en formato JSON.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Número máximo de resultados (defecto: 30, máx: 500).")] = 30,
) -> int:
    """Ejecuta la búsqueda FTS5 en la DB para la versión dada. Si output_json es True, solo imprime JSON."""
    root: Path = ctx.obj["root"]

    if not term.strip():
        out.error(i18n.t("cli.query.usage"))
        return 1
    if version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    
    with out.status(i18n.t("cli.query.searching", term=term, version=version)):
        results, err = search.search_api(root, version, term.strip(), limit=limit)

    if err is not None:
        out.error(err["message"])
        if err.get("hint"):
            out.error(err["hint"])
        return 1
        
    if json_output:
        json_output_data = {"version": version, "term": term.strip(), "count": len(results), "results": results}
        print(json.dumps(json_output_data, ensure_ascii=False))
        return 0

    if not results:
        out.success(i18n.t("cli.query.no_results", term=term, version=version))
        return 0

    out.phase(i18n.t("cli.query.result_count", count=len(results), term=term, version=version))
    
    columns = ["package", "class_name", "kind", "method_name", "params", "returns"]
    out.table(
        title=i18n.t("cli.query.table_title"),
        data=results,
        columns=columns
    )
    
    return 0

# La función run_query se elimina porque Typer se encarga del dispatching.