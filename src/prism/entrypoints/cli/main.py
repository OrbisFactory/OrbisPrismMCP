# Punto de entrada del CLI: dispatch por subcomando.

import sys
from pathlib import Path

# import colorama #!ELIMINAR

from ... import i18n
from ...infrastructure import config_impl

from . import context
from . import help as cli_help
from . import lang
from . import config_cmd
from . import query
from . import mcp_cmd


from .parser import create_parser # NEW IMPORT
from . import branding #!NUEVA_IMPORTACION

def main() -> int:
    """CLI entry point."""
    # colorama.init() #!ELIMINAR

    #_ Muestra el logo al inicio
    branding.print_logo() #!NUEVA_LLAMADA_FUNCION

    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    root = config_impl.get_project_root()

    # NEW DISPATCH LOGIC WILL GO HERE
    # Temporarily return 0 to allow building the dispatch logic progressively.
    if args.command == "config_impl":
        return config_cmd.run_config(args, root)
    elif args.command == "query":
        return query.run_query(args, root)
    elif args.command == "mcp":
        return mcp_cmd.run_mcp(args, root)
    elif args.command in ("context", "ctx"):
        return context.run_context(args, root)
    elif args.command == "lang":
        return lang.run_lang(args, root)
    else:
        # This case should ideally not be reached due to required=True in subparsers,
        # but good for safety.
        print(i18n.t("cli.unknown_command", cmd=args.command), file=sys.stderr)
        cli_help.print_help() # Re-add general help print for unknown commands
        return 1
