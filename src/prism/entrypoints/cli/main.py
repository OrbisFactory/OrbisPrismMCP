# Punto de entrada del CLI: dispatch por subcomando.

import sys
from pathlib import Path
from typing_extensions import Annotated

import typer

from ... import i18n
from ...infrastructure import config_impl

from . import branding
from . import context
from . import lang
from . import config #!AJUSTE_IMPORTACION
from . import query
from . import mcp_cmd


#_ Creamos la aplicación principal de Typer
app = typer.Typer(
    name="prism",
    help="Orbis Prism MCP - Hytale Modding Toolkit."
)

#_ Añadimos el logo al inicio de la aplicación
@app.callback()
def main_callback(
    ctx: typer.Context,
):  
    """Muestra el logo al inicio y establece el contexto de la raíz del proyecto."""
    branding.print_logo()
    ctx.ensure_object(dict)
    ctx.obj["root"] = config_impl.get_project_root()


#_ Agregamos los subcomandos al CLI principal
#_ Cada módulo de comando (context, query, etc.) se convertirÃ¡ en un sub-aplicación de Typer.
app.add_typer(context.app, name="context", aliases=["ctx"], help=i18n.t("cli.context.help"))
app.add_typer(query.app, name="query", help=i18n.t("cli.query.help"))
app.add_typer(mcp_cmd.app, name="mcp", help=i18n.t("cli.mcp.help"))
app.add_typer(lang.app, name="lang", help=i18n.t("cli.lang.help"))
app.add_typer(config_cmd.app, name="config", help=i18n.t("cli.config.help")) # Renombramos config_impl a config para el CLI

def main() -> int:
    """CLI entry point."""
    #_ Typer maneja la inicialización de colorama y la gestión de argumentos
    app()
    return 0