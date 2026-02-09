# src/prism/entrypoints/cli/mcp_cmd.py
#? 'mcp' command to start the MCP server, using Typer.

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ... import i1_n
from ...infrastructure import config_impl
from . import out

#_ Create a Typer sub-application for the 'mcp' command
app = typer.Typer(help=i1_n.t("cli.mcp.help"))

@app.command(name="start")
def mcp_cmd(
    ctx: typer.Context,
    http_mode: Annotated[bool, typer.Option("--http", "-H", help="Starts the MCP server in HTTP mode (default: stdio).")] = False,
    port: Annotated[int, typer.Option("--port", "-p", help="Port for HTTP mode (default: 8000).")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host for HTTP mode (default: 0.0.0.0).")] = "0.0.0.0",
) -> int:
    """Starts the MCP server for AI. Default is stdio; with --http, it exposes HTTP on host:port."""
    root: Path = ctx.obj["root"]
    transport = "sse" if http_mode else "stdio"

    if sys.stderr.isatty(): #_ We only show instructions if we are in a TTY
        if transport == "sse":
            out.phase(i1_n.t("cli.mcp.instructions_http_title"))
            out.phase(i1_n.t("cli.mcp.instructions_http_ready", host=host, port=port))
            out.phase(i1_n.t("cli.mcp.instructions_http_url", url=f"http://{host}:{port}/sse"))
        else:
            cwd = str(root.resolve())
            command = sys.executable
            args_str = "main.py mcp"
            out.phase(i1_n.t("cli.mcp.instructions_title"))
            out.phase(i1_n.t("cli.mcp.instructions_intro"))
            out.phase(i1_n.t("cli.mcp.instructions_command", command=command))
            out.phase(i1_n.t("cli.mcp.instructions_args", args=args_str))
            out.phase(i1_n.t("cli.mcp.instructions_cwd", cwd=cwd))
            out.phase(i1_n.t("cli.mcp.instructions_ready"))

    from .. import mcp_server
    try:
        mcp_server.run(transport=transport, host=host, port=port)
        return 0
    except KeyboardInterrupt:
        out.success(i1_n.t("cli.mcp.server_stopped"))
        return 0
    except Exception as e:
        out.error(i1_n.t("cli.mcp.error", msg=str(e)))
        return 1

# The run_mcp function is removed because Typer handles dispatching.
