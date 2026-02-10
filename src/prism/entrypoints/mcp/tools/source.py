# src/prism/entrypoints/mcp/tools/source.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import read_source as app_read_source
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository


def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers source code reading and FTS help tools."""

    def prism_read_source(
        version: str,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        norm_version = normalize_version(version)
        payload = app_read_source(config, None, norm_version, file_path, start_line=start_line, end_line=end_line)
        if "error" in payload:
            return json.dumps({"error": payload["error"], "message": payload["message"]}, ensure_ascii=False)
        return json.dumps(payload, ensure_ascii=False)

    prism_read_source.__doc__ = i18n.t("mcp.tools.prism_read_source.description")
    app.tool()(prism_read_source)

    def prism_fts_help() -> str:
        return (
            "FTS5 search syntax (prism_search):\n"
            "- Single word: matches that token.\n"
            '- Quoted phrase: "exact phrase" matches the exact phrase.\n'
            "- AND: term1 AND term2 (both must appear).\n"
            "- OR: term1 OR term2 (either can appear).\n"
            "- Prefix: term* matches tokens that start with 'term'.\n"
            'Examples: GameManager, "getPlayer" AND server, spawn OR despawn.'
        )


    prism_fts_help.__doc__ = i18n.t("mcp.tools.prism_fts_help.description")
    app.tool()(prism_fts_help)
