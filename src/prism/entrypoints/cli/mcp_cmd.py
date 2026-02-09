# src/prism/entrypoints/cli/mcp_cmd.py
#? 'mcp' command to start the MCP server, using Typer.

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ... import i18n
from ...infrastructure import config_impl
from . import out

def mcp_callback(
    ctx: typer.Context,
    http_mode: Annotated[bool, typer.Option("--http", "-H", help=i18n.t("cli.mcp.http_help"), rich_help_panel="Network Options")] = False,
    port: Annotated[int, typer.Option("--port", "-p", help=i18n.t("cli.mcp.port_help"), rich_help_panel="Network Options")] = 8000,
    host: Annotated[str, typer.Option("--host", help=i18n.t("cli.mcp.host_help"), rich_help_panel="Network Options")] = "0.0.0.0",
) -> int:
    """
    Starts the MCP server for AI.
    Default mode is stdio. Use --http to expose an HTTP endpoint.
    """
    root: Path = ctx.obj["root"]
    transport = "sse" if http_mode else "stdio"

    if sys.stderr.isatty(): #_ We only show instructions if we are in a TTY
        if transport == "sse":
            out.phase(i18n.t("cli.mcp.instructions_http_title"))
            out.phase(i18n.t("cli.mcp.instructions_http_ready", host=host, port=port))
            out.phase(i18n.t("cli.mcp.instructions_http_url", url=f"http://{host}:{port}/sse"))
        else:
            cwd = str(root.resolve())
            command = sys.executable
            args_str = "main.py mcp"
            out.phase(i18n.t("cli.mcp.instructions_title"))
            out.phase(i18n.t("cli.mcp.instructions_intro"))
            out.phase(i18n.t("cli.mcp.instructions_command", command=command))
            out.phase(i18n.t("cli.mcp.instructions_args", args=args_str))
            out.phase(i18n.t("cli.mcp.instructions_cwd", cwd=cwd))
            out.phase(i18n.t("cli.mcp.instructions_ready"))

    from .. import mcp_server
    try:
        mcp_server.run(transport=transport, host=host, port=port)
        return 0
    except KeyboardInterrupt:
        out.success(i18n.t("cli.mcp.server_stopped"))
        return 0
    except Exception as e:
        out.error(i18n.t("cli.mcp.error", msg=str(e)))
        raise typer.Exit(code=1)
