# CLI entry point: dispatch by subcommand.

import sys
from pathlib import Path
from typing_extensions import Annotated

import typer

from ... import i18n, __version__
from ...infrastructure import config_impl

from . import branding
from . import context
from . import lang
from . import config
from . import query
from . import mcp_cmd


#_ Create the main Typer application
app = typer.Typer(
    name="prism",
    help=i18n.t("cli.help.title"),
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False
)
#_ Localize Typer Rich help headers
try:
    import typer.rich_utils as r
    r.COMMANDS_PANEL_TITLE = i18n.t("cli.help.commands_panel")
    r.OPTIONS_PANEL_TITLE = i18n.t("cli.help.options_panel")
    r.ARGUMENTS_PANEL_TITLE = i18n.t("cli.help.arguments_panel")
except ImportError:
    pass

def version_callback(value: bool):
    """Callback for the --version flag."""
    if value:
        #_ Logo is already printed in main(), so we just exit
        raise typer.Exit()

@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Annotated[bool | None, typer.Option("--version", "-v", callback=version_callback, is_eager=True, help=i18n.t("cli.help.version"))] = None,
    workspace: Annotated[Path | None, typer.Option("--workspace", "-w", help="Path to the Hytale project workspace")] = None,
):  
    """Sets the project root context."""
    #_ Determine if we allow global fallback (~/.prism)
    allow_global = True

    ctx.ensure_object(dict)
    root = config_impl.get_project_root(override_root=workspace)
    ctx.obj["root"] = root
    


#_ Add subcommands to the main CLI
#_ Each command module (context, query, etc.) will become a Typer sub-application.
app.add_typer(context.app, name="context", help=i18n.t("cli.context.help"))
app.add_typer(context.app, name="ctx", help=i18n.t("cli.ctx.help")) # Add alias for context
app.command(name="query", help=i18n.t("cli.query.help"))(query.query_callback)
app.command(name="mcp", help=i18n.t("cli.mcp.help"))(mcp_cmd.mcp_callback)
app.add_typer(lang.app, name="lang", help=i18n.t("cli.lang.help"))
app.add_typer(config.app, name="config", help=f"{i18n.t('cli.config.help')} (game_path, jadx_path, decompiler)") 

def main() -> int:
    """CLI entry point."""
    branding.print_logo()
    #_ Typer handles colorama initialization and argument management
    app()
    return 0
