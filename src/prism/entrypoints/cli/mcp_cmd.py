# src/prism/entrypoints/cli/mcp_cmd.py
#? 'mcp' command to start the MCP server, using Typer.

import sys
import json
import shlex
from pathlib import Path
from typing import Optional, Annotated, Dict, Any

import typer
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich import box

from ... import i18n
from ...infrastructure import config_impl
from . import out

def _get_client_configs(root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Returns the configuration for different MCP clients.
    """
    cwd = str(root.resolve())
    
    # Use sys.executable -m prism for maximum reliability across environments
    command = sys.executable
    args = ["-m", "prism", "mcp"]
    
    return {
        "OpenCode": {
            "name": i18n.t("cli.mcp.client_opencode"),
            "command": command,
            "args": args,
            "cwd": cwd,
            "type": "json"
        },
        "Cursor": {
            "name": i18n.t("cli.mcp.client_cursor"),
            "command": command,
            "args": args,
            "cwd": cwd,
            "type": "json"
        },
        "VSCode": {
            "name": i18n.t("cli.mcp.client_vscode"),
            "command": command,
            "args": args,
            "cwd": cwd,
            "type": "json"
        },
        "Antigravity": {
            "name": i18n.t("cli.mcp.client_antigravity"),
            "command": command,
            "args": args,
            "cwd": cwd,
            "type": "json"
        },
        "Gemini": {
            "name": i18n.t("cli.mcp.client_gemini"),
            "command": command,
            "args": args,
            "cwd": cwd,
            "type": "command"
        }
    }

def mcp_callback(
    ctx: typer.Context,
    http_mode: Annotated[bool, typer.Option("--http", "-H", help=i18n.t("cli.mcp.http_help"))] = False,
    port: Annotated[int, typer.Option("--port", "-p", help=i18n.t("cli.mcp.port_help"))] = 8000,
    host: Annotated[str, typer.Option("--host", help=i18n.t("cli.mcp.host_help"))] = "127.0.0.1",
) -> int:
    """
    Starts the MCP server for AI.
    Default mode is stdio. Use --http to expose an HTTP endpoint.
    """
    root: Path = ctx.obj["root"]
    transport = "sse" if http_mode else "stdio"

    if sys.stderr.isatty():
        console = Console(stderr=True)
        if transport == "sse":
            console.print(Panel(
                f"[bold cyan]http://{host}:{port}/sse[/bold cyan]",
                title=f"[bold magenta]{i18n.t('cli.mcp.instructions_http_title')}[/bold magenta]",
                subtitle=i18n.t("cli.mcp.instructions_http_ready", host=host, port=port),
                box=box.ROUNDED,
                expand=True
            ))
        else:
            configs = _get_client_configs(root)
            
            table = Table(
                title=f"[bold magenta]{i18n.t('cli.mcp.instructions_title')}[/bold magenta]",
                box=box.ROUNDED,
                expand=True
            )

            
            table.add_column(i18n.t("cli.mcp.table.client"), style="cyan", no_wrap=True)
            table.add_column(i18n.t("cli.mcp.table.config"), style="green")
            
            for cfg in configs.values():
                if cfg["type"] == "json":
                    # For clients like Cursor, VSCode, OpenCode, we use a standard JSON snippet
                    config_snippet = {
                        "command": cfg["command"],
                        "args": cfg["args"],
                        "cwd": cfg["cwd"]
                    }
                    formatted = json.dumps(config_snippet, indent=2)
                else:
                    # For command-line clients (Gemini-CLI), we use a joined string
                    formatted = shlex.join([cfg["command"]] + cfg["args"])
                
                table.add_row(cfg["name"], formatted)
            
            console.print(table)
            out.phase(i18n.t("cli.mcp.instructions_ready"))


    from ..mcp import main
    try:
        main.run(transport=transport, host=host, port=port)
        return 0
    except KeyboardInterrupt:
        out.success(i18n.t("cli.mcp.server_stopped"))
        return 0
    except Exception as e:
        out.error(i18n.t("cli.mcp.error", msg=str(e)))
        raise typer.Exit(code=1)
