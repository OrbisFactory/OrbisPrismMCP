# src/prism/entrypoints/cli/mcp_cmd.py
#? Comando 'mcp' para iniciar el servidor MCP, con Typer.

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ... import i18n
from ...infrastructure import config_impl
from . import out

#_ Creamos una sub-aplicación de Typer para el comando 'mcp'
app = typer.Typer(help=i18n.t("cli.mcp.help"))

@app.command(name="start")
def mcp_cmd(
    ctx: typer.Context,
    http_mode: Annotated[bool, typer.Option("--http", "-H", help="Inicia el servidor MCP en modo HTTP (por defecto: stdio).")] = False,
    port: Annotated[int, typer.Option("--port", "-p", help="Puerto para el modo HTTP (defecto: 8000).")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host para el modo HTTP (defecto: 0.0.0.0).")] = "0.0.0.0",
) -> int:
    """Inicia el servidor MCP para IA. Por defecto stdio; con --http expone HTTP en el host:puerto."""
    root: Path = ctx.obj["root"]
    transport = "sse" if http_mode else "stdio"

    if sys.stderr.isatty(): #_ Solo mostramos instrucciones si estamos en una TTY
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
        return 1

# La función run_mcp se elimina porque Typer se encarga del dispatching.