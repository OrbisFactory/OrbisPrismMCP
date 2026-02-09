# src/prism/entrypoints/cli/lang.py
#? 'lang' commands for managing the CLI language, using Typer.

import sys
from pathlib import Path
from typing import Tuple

import typer
from typing_extensions import Annotated

from ... import i18n
from ...infrastructure import config_impl
from . import out

#_ Create a Typer sub-application for the 'lang' commands
app = typer.Typer(help=i18n.t("cli.lang.help"))

@app.command(name="list")
def list_cmd(
    ctx: typer.Context
) -> int:
    """Lists available languages and marks the current one."""
    root: Path = ctx.obj["root"]
    current = i18n.get_current_locale(root)
    locales: list[Tuple[str, str]] = i18n.get_available_locales()

    table_data = []
    for code, name in locales:
        is_current = "✔" if code == current else ""
        table_data.append({"code": code, "name": name, "current": is_current})

    out.table(
        title=i18n.t("lang.list.header"),
        data=table_data,
        columns=["code", "name", "current"]
    )
    return 0

@app.command(name="set")
def set_cmd(
    ctx: typer.Context,
    lang_code: Annotated[str, typer.Argument(help="Language code (e.g., \"en\", \"es\").", 
                                            choices=[code for code, _ in i18n.get_available_locales()])]
) -> int:
    """Changes the language saved in .prism.json."""
    root: Path = ctx.obj["root"]
    code = lang_code.strip().lower()
    
    if not i18n.is_locale_available(code):
        out.error(i18n.t("lang.set.invalid", lang=code))
        return 1

    cfg = config_impl.load_config(root)
    cfg[config_impl.CONFIG_KEY_LANG] = code
    config_impl.save_config(cfg, root)
    out.success(i18n.t("lang.set.success", lang=code))
    return 0

# The run_lang function is removed because Typer handles dispatching.
