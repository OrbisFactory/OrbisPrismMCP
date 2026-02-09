# query command: FTS5 search in the DB.

import json
import sys
from pathlib import Path
import argparse # NEW IMPORT

from ...application import search
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl

# from . import args as cli_args # REMOVED


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
        print(i18n.t("cli.query.usage"), file=sys.stderr)
        return 1
    if version not in VALID_SERVER_VERSIONS:
        print(i18n.t("cli.context.use.invalid"), file=sys.stderr)
        return 1
    results, err = search.search_api(root, version, query_term.strip(), limit=limit)
    if err is not None:
        print(err["message"], file=sys.stderr)
        if err.get("hint"):
            print(err["hint"], file=sys.stderr)
        return 1
    if output_json:
        out = {"version": version, "term": query_term.strip(), "count": len(results), "results": results}
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print(i18n.t("cli.query.result_count", count=len(results), term=query_term, version=version))
    for r in results:
        print(f"  {r['package']}.{r['class_name']} ({r['kind']}) :: {r['method_name']}({r['params']}) -> {r['returns']}")
    return 0


def run_query(args: argparse.Namespace, root: Path) -> int:
    """Dispatch of the query command."""
    if not args.term:
        print(i18n.t("cli.query.usage"), file=sys.stderr)
        return 1
    return cmd_query(root, query_term=args.term, version=args.version, limit=args.limit, output_json=args.json)
