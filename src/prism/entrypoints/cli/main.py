# CLI entry point: dispatch by subcommand.

import sys
from pathlib import Path
from typing_extensions import Annotated

import typer

from ... import i18n
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
@app.callback()
def main_callback(
    ctx: typer.Context,
):  
    """Sets the project root context."""
    ctx.ensure_object(dict)
    root = config_impl.get_project_root()
    ctx.obj["root"] = root
    
    #_ Localize Typer Rich help headers
    try:
        import typer.rich_utils as r
        r.COMMANDS_PANEL_TITLE = i18n.t("cli.help.commands_panel")
        r.OPTIONS_PANEL_TITLE = i18n.t("cli.help.options_panel")
        r.ARGUMENTS_PANEL_TITLE = i18n.t("cli.help.arguments_panel")
    except ImportError:
        pass


#_ Add subcommands to the main CLI
#_ Each command module (context, query, etc.) will become a Typer sub-application.
app.add_typer(context.app, name="context", help=i18n.t("cli.context.help"))
app.add_typer(context.app, name="ctx", help=i18n.t("cli.ctx.help")) # Add alias for context
app.command(name="query", help=i18n.t("cli.query.help"))(query.query_callback)
app.command(name="mcp", help=i18n.t("cli.mcp.help"))(mcp_cmd.mcp_callback)
app.add_typer(lang.app, name="lang", help=i18n.t("cli.lang.help"))
app.add_typer(config.app, name="config", help=i18n.t("cli.config.help")) # We rename config_impl to config for the CLI

def main() -> int:
    """CLI entry point."""
    branding.print_logo()
    #_ Typer handles colorama initialization and argument management
    app()
    return 0
