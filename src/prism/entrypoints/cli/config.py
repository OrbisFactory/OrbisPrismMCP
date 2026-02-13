# src/prism/entrypoints/cli/config.py
#? 'config' commands for managing internal configuration, using Typer.

import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ... import i18n
from ...infrastructure import config_impl
from ...infrastructure import detection
from . import out

#_ Create a Typer sub-application for the 'config' commands
app = typer.Typer(help=i18n.t("cli.config.help"))

@app.command(name="set", help=i18n.t("cli.config.set_help"))
def set_config_cmd(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help=i18n.t("cli.config.key_help"))],
    value: Annotated[str, typer.Argument(help=i18n.t("cli.config.value_help"))],
) -> int:
    """Sets a configuration key-value pair."""
    root: Path = ctx.obj["root"]

    if key == "game_path":
        path = Path(value).resolve()
        cfg = config_impl.load_config(root)

        if path.is_dir() and detection.is_hytale_root(path):
            release_jar, prerelease_jar = detection.find_jar_paths_from_hytale_root(path)
            if not release_jar and not prerelease_jar:
                out.error(i18n.t("cli.config.jar_set_invalid", path=value))
                return 1
            if release_jar:
                cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(release_jar.resolve())
                if prerelease_jar:
                    cfg[config_impl.CONFIG_KEY_JAR_PATH_PRERELEASE] = str(prerelease_jar.resolve())
            else:
                cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(prerelease_jar.resolve())
            config_impl.save_config(cfg, root)
            out.success(i18n.t("cli.config.hytale_root_detected"))
            if release_jar:
                out.success(i18n.t("cli.init.success_jar", path=release_jar))
            if prerelease_jar:
                out.success(i18n.t("cli.init.sibling_saved", path=prerelease_jar))
            return 0
        if not detection.is_valid_jar(path):
            out.error(i18n.t("cli.config.jar_set_invalid", path=value))
            return 1
        cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(path)
        sibling = detection.get_sibling_version_jar_path(path)
        if sibling:
            if "pre-release" in str(path).replace("\\", "/"):
                cfg[config_impl.CONFIG_KEY_JAR_PATH_RELEASE] = str(sibling.resolve())
            else:
                cfg[config_impl.CONFIG_KEY_JAR_PATH_PRERELEASE] = str(sibling.resolve())
        config_impl.save_config(cfg, root)
        out.success(i18n.t("cli.config.jar_set_success", path=path))
        if sibling:
            out.success(i18n.t("cli.init.sibling_saved", path=sibling))
        return 0
    elif key == "jadx_path":
        j_path = Path(value).resolve()
        if not j_path.is_file():
            out.error(i18n.t("cli.config.jadx_path_invalid", path=value))
            return 1
        cfg = config_impl.load_config(root)
        cfg[config_impl.CONFIG_KEY_JADX_PATH] = str(j_path)
        config_impl.save_config(cfg, root)
        out.success(i18n.t("cli.config.jadx_path_set_success", path=j_path))
        return 0
    elif key == "decompiler":
        val = value.lower().strip()
        if val not in ["jadx", "vineflower"]:
            out.error(i18n.t("cli.config.decompiler_invalid", value=value))
            return 1
        cfg = config_impl.load_config(root)
        cfg[config_impl.CONFIG_KEY_DECOMPILER] = val
        config_impl.save_config(cfg, root)
        out.success(i18n.t("cli.config.decompiler_set_success", engine=val))
        return 0
    else:
        out.error(i18n.t("cli.config.unknown_key", key=key))
        return 1

# The run_config function is removed because Typer handles dispatching.
