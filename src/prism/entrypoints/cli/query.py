# src/prism/entrypoints/cli/query.py
#? 'query' command for FTS5 search in the DB, using Typer.

import json
from pathlib import Path
from typing import Optional, Annotated
from enum import Enum

import typer

from ...application import search
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl
from ...infrastructure.file_config import FileConfigProvider
from ...infrastructure.sqlite_repository import SqliteIndexRepository
from . import out

#_ Create a dynamic Enum for the server versions for Typer's choice validation
VersionEnum = Enum("VersionEnum", {v: v for v in VALID_SERVER_VERSIONS})

def query_callback(
    ctx: typer.Context,
    term: Annotated[str, typer.Argument(help=i18n.t("cli.query.term_help"))],
    version: Annotated[VersionEnum, typer.Option("--version", "-v", help=i18n.t("cli.query.version_help"))] = VersionEnum.release,
    json_output: Annotated[bool, typer.Option("--json", "-j", help=i18n.t("cli.query.json_help"))] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", help=i18n.t("cli.query.limit_help"))] = 30,
    assets: Annotated[bool, typer.Option("--assets", "-a", help="Busca en el índice de assets en lugar de la API de código.")] = False,
) -> int:
    """
    Executes an FTS5 search in the DB for the given version.
    """
    root: Path = ctx.obj["root"]
    version_str = version.value

    if not term.strip():
        out.error(i18n.t("cli.query.usage"))
        raise typer.Exit(code=1)
    
    if assets:
        from ...infrastructure import sqlite_assets_repository
        from ...application import assets_use_cases
        
        db_path = config_impl.get_assets_db_path(root, version_str)
        if not db_path.exists():
            out.error(f"Base de datos de assets para {version_str} no encontrada.")
            raise typer.Exit(code=1)
            
        repo = sqlite_assets_repository.SqliteAssetsRepository()
        use_cases = assets_use_cases.AssetsUseCases(repo)
        
        with out.status(f"Buscando asset '{term}' en {version_str}..."):
            results = use_cases.search_assets(db_path, term, limit)
            
        if json_output:
            print(json.dumps([vars(a) for a in results], ensure_ascii=False))
            return 0
            
        if not results:
            out.success(f"No se encontraron assets para '{term}' en {version_str}.")
            return 0
            
        out.phase(f"Se encontraron {len(results)} assets para '{term}' ({version_str}):")
        
        data = []
        for a in results:
            row = {
                "path": a.path,
                "category": a.category or "-",
                "id": a.internal_id or "-",
                "size": f"{a.size / 1024:.1f} KB"
            }
            if a.width and a.height:
                row["dims"] = f"{a.width}x{a.height}"
            else:
                row["dims"] = "-"
            data.append(row)
            
        out.table(title="Resultados de Assets", data=data, columns=["path", "category", "id", "dims", "size"])
        return 0

    config_provider = FileConfigProvider()
    index_repository = SqliteIndexRepository()
    
    with out.status(i18n.t("cli.query.searching", term=term, version=version_str)):
        results, err = search.search_api(
            config_provider, 
            index_repository, 
            root, 
            version_str, 
            term.strip(), 
            limit=limit,
            t=i18n.t
        )

    if err is not None:
        out.error(err["message"])
        if err.get("hint"):
            out.error(err["hint"])
        raise typer.Exit(code=1)
        
    if json_output:
        json_output_data = {"version": version_str, "term": term.strip(), "count": len(results), "results": results}
        print(json.dumps(json_output_data, ensure_ascii=False))
        return 0

    if not results:
        out.success(i18n.t("cli.query.no_results", term=term, version=version_str))
        return 0

    out.phase(i18n.t("cli.query.result_count", count=len(results), term=term, version=version_str))
    
    columns = ["package", "class_name", "kind", "method_name", "params", "returns"]
    out.table(
        title=i18n.t("cli.query.table_title"),
        data=results,
        columns=columns
    )
    
    return 0
