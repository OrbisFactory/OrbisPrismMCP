# src/prism/entrypoints/cli/query.py
#? 'query' command for FTS5 search in the DB, using Typer.

import json
from pathlib import Path
from typing import Optional
from enum import Enum

import typer
from typing_extensions import Annotated

from ...application import search
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl
from . import out

#_ Create a dynamic Enum for the server versions for Typer's choice validation
VersionEnum = Enum("VersionEnum", {v: v for v in VALID_SERVER_VERSIONS})


#_ Create a Typer sub-application for the 'query' command
app = typer.Typer(help=i18n.t("cli.query.help"))

@app.command(name="search")
def query_cmd(
    ctx: typer.Context,
    term: Annotated[str, typer.Argument(help="Search term (Rust-flavored regex by default, use \\b for word boundaries).")] = "",
    version: Annotated[VersionEnum, typer.Argument(help="Version to query (release, prerelease).")] = VersionEnum.release,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output results in JSON format.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum number of results (default: 30, max: 500).")] = 30,
) -> int:
    """Executes FTS5 search in the DB for the given version. If json_output is True, only prints JSON."""
    root: Path = ctx.obj["root"]
    version_str = version.value

    if not term.strip():
        out.error(i18n.t("cli.query.usage"))
        return 1
    
    with out.status(i18n.t("cli.query.searching", term=term, version=version_str)):
        results, err = search.search_api(root, version_str, term.strip(), limit=limit)

    if err is not None:
        out.error(err["message"])
        if err.get("hint"):
            out.error(err["hint"])
        return 1
        
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

# The run_query function is removed because Typer handles dispatching.