# src/prism/entrypoints/cli/context.py
#? 'context' / 'ctx' commands for workspace management, using Typer.

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from ...application import get_context_list
from ... import i18n
from ...domain.constants import VALID_SERVER_VERSIONS
from ...infrastructure import config_impl
from ...infrastructure import decompile
from ...infrastructure import detection
from ...infrastructure import extractor
from ...infrastructure import file_config
from ...infrastructure import prune
from ...infrastructure import workspace_cleanup

from . import out

#_ Create a Typer sub-application for the 'context' commands
app = typer.Typer(help=i18n.t("cli.context.help"))

def _ensure_dirs(root: Path) -> None:
    """Ensures that the workspace, decompiled, db, and logs directories exist."""
    config_impl.get_workspace_dir(root).mkdir(parents=True, exist_ok=True)
    (config_impl.get_workspace_dir(root) / "server").mkdir(parents=True, exist_ok=True)
    config_impl.get_decompiled_dir(root).mkdir(parents=True, exist_ok=True)
    config_impl.get_db_dir(root).mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)

def _cmd_init_logic(root: Path) -> int:
    """Internal logic to detect HytaleServer.jar and save the configuration."""
    _ensure_dirs(root)

    env_jar = os.environ.get(config_impl.ENV_JAR_PATH)
    if env_jar:
        env_path = Path(env_jar).resolve()
        if not detection.is_valid_jar(env_path):
            out.error(i18n.t("cli.init.env_jar_invalid"))
            return 1

    jar_path = detection.find_and_validate_jar(root)
    if jar_path is None:
        out.error(i18n.t("cli.init.jar_not_found"))
        out.error(i18n.t("cli.init.hint_env"))
        out.error(i18n.t("cli.init.hint_windows"))
        return 1

    cfg = config_impl.load_config(root)
    cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(jar_path.resolve())
    cfg[config_impl.CONFIG_KEY_OUTPUT_DIR] = str(config_impl.get_workspace_dir(root).resolve())
    cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(jar_path.resolve())
    cfg[config_impl.CONFIG_KEY_OUTPUT_DIR] = str(config_impl.get_workspace_dir(root).resolve())
    sibling = detection.get_sibling_version_jar_path(jar_path)
    if sibling:
        if "pre-release" in str(jar_path).replace("\\", "/"):
            cfg[config_impl.CONFIG_KEY_JAR_PATH_RELEASE] = str(sibling.resolve())
        else:
            cfg[config_impl.CONFIG_KEY_JAR_PATH_PRERELEASE] = str(sibling.resolve())
    config_impl.save_config(cfg, root)

    out.success(i18n.t("cli.init.success_jar", path=jar_path))
    if sibling:
        out.success(i18n.t("cli.init.sibling_saved", path=sibling))
    out.success(i18n.t("cli.init.success_config", path=config_impl.get_config_path(root)))
    return 0

def _resolve_context_versions(root: Path, version: str | None, default_to_all: bool = True) -> list[str] | None:
    """Determines the list of versions to use; None if no JAR is configured."""
    if version is not None and version != "all":
        return [version]
    
    if version is None and not default_to_all:
        return [config_impl.get_active_version(root)]

    versions = []
    if config_impl.get_jar_path_release_from_config(root):
        versions.append("release")
    if config_impl.get_jar_path_prerelease_from_config(root):
        versions.append("prerelease")
    if not versions and config_impl.get_jar_path_from_config(root):
        versions = ["release"]
    return versions if versions else None


@app.command(name="detect", help=i18n.t("cli.help.context_detect_desc"))
def detect_cmd(
    ctx: typer.Context
) -> int:
    """Detects HytaleServer.jar and saves the configuration."""
    root: Path = ctx.obj["root"]
    return _cmd_init_logic(root)


@app.command(name="init", help=i18n.t("cli.help.context_init_desc"))
def init_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help=i18n.t("cli.init.version_help"))] = None,
    all_versions: Annotated[bool, typer.Option("--all", "-a", help=i18n.t("cli.init.all_help"))] = False,
) -> int:
    """Full pipeline: detects, decompiles, prunes, and indexes."""
    root: Path = ctx.obj["root"]
    
    if _cmd_init_logic(root) != 0:
        return 1
    
    if version is not None and version != "all" and version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1

    if all_versions or version == "all":
        versions_list = _resolve_context_versions(root, "all")
    elif version:
        versions_list = [version]
    else:
        #_ Default: only release
        versions_list = ["release"]

    if not versions_list:
        out.error(i18n.t("cli.decompile.no_jar"))
        return 1

    out.phase(i18n.t("cli.build.phase_decompile"))
    
    #_ run_decompile_only already handles its own Progress bar, we avoid nesting out.status to prevent flickering
    success, err = decompile.run_decompile_only(root, versions=versions_list)
    
    if not success:
        out.error(i18n.t("cli.build.decompile_failed"))
        out.error(i18n.t(f"cli.decompile.{err}"))
        return 1
    out.phase(i18n.t("cli.build.phase_decompile_done"))

    out.phase(i18n.t("cli.build.phase_prune"))
    #_ run_prune_only already handles its own Progress bar
    success, err = prune.run_prune_only(root, versions=versions_list)

    if not success:
        out.error(i18n.t("cli.prune." + err))
        return 1
    out.phase(i18n.t("cli.prune.completed_all"))


    out.phase(i18n.t("cli.build.phase_index"))
    for v in versions_list:
        #_ extractor.run_index already handles its own Progress bar
        ok, payload = extractor.run_index(root, v)
        if ok:
            classes, methods, constants = payload
            out.success(i18n.t("cli.build.indexed", version=v, classes=classes, methods=methods, constants=constants))
        elif payload == "no_decompiled":
            out.phase(i18n.t("cli.build.skipped_no_code", version=v))
        else:
            out.error(i18n.t("cli.index.db_error"))
            return 1
    out.success(i18n.t("cli.build.success"))
    return 0


@app.command(name="clean", help=i18n.t("cli.help.context_clean_desc"))
def clean_cmd(
    ctx: typer.Context,
    target: Annotated[str, typer.Argument(help="Target to clean: 'db' (databases only), 'build' (decompiled files), or 'all'.",
                                         rich_help_panel="Cleaning Options")],
) -> int:
    """Cleans workspace artifacts (db, build, all)."""
    root: Path = ctx.obj["root"]
    t = target.strip().lower()

    if t == "db":
        with out.status(i18n.t("cli.context.clean.cleaning_db")):
            workspace_cleanup.clean_db(root)
        out.success(i18n.t("cli.context.clean.db_done"))
        return 0
    if t in ("build", "b"):
        with out.status(i18n.t("cli.context.clean.cleaning_build")):
            workspace_cleanup.clean_build(root)
        out.success(i18n.t("cli.context.clean.build_done"))
        return 0
    if t == "all":
        if not typer.confirm(i18n.t("cli.context.clean.confirm_all")):
            raise typer.Abort()
        with out.status(i18n.t("cli.context.clean.cleaning_all")):
            workspace_cleanup.clean_db(root)
            workspace_cleanup.clean_build(root)
        out.success(i18n.t("cli.context.clean.all_done"))
        return 0
    out.error(i18n.t("cli.context.clean.usage"))
    return 1


@app.command(name="reset", help=i18n.t("cli.help.context_reset_desc"))
def reset_cmd(
    ctx: typer.Context
) -> int:
    """Resets the project to zero: cleans db + build and removes .prism.json."""
    root: Path = ctx.obj["root"]
    if not typer.confirm(i18n.t("cli.context.reset.confirm")):
        raise typer.Abort()
    
    with out.status(i18n.t("cli.context.reset.reseting")):
        workspace_cleanup.reset_workspace(root)
    out.success(i18n.t("cli.context.reset.done"))
    return 0


@app.command(name="decompile", help=i18n.t("cli.help.context_decompile_desc"))
def decompile_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Specific version to decompile (release, prerelease), or 'all'.")] = None,
) -> int:
    """JADX only → decompiled_raw (without pruning)."""
    root: Path = ctx.obj["root"]
    if version is not None and version != "all" and version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    
    versions = _resolve_context_versions(root, version, default_to_all=False)

    #_ Removed nested out.status
    success, err = decompile.run_decompile_only(root, versions=versions)

    if success:
        out.success(i18n.t("cli.decompile.success"))
        return 0
    out.error(i18n.t(f"cli.decompile.{err}"))
    return 1


@app.command(name="prune", help=i18n.t("cli.help.context_prune_desc"))
def prune_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Specific version to prune (release, prerelease), or 'all'.")] = None,
) -> int:
    """Pruning only (raw → decompiled)."""
    root: Path = ctx.obj["root"]
    if version is not None and version != "all" and version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1

    versions = _resolve_context_versions(root, version, default_to_all=False)
    
    out.phase(i18n.t("cli.prune.pruning"))
    #_ Removed nested out.status
    success, err = prune.run_prune_only(root, versions=versions)

    if success:
        if version:
            out.success(i18n.t("cli.prune.success", version=version))
        else:
            out.success(i18n.t("cli.prune.completed_all"))
        return 0
    out.error(i18n.t(f"cli.prune.{err}"))
    return 1


@app.command(name="db", help=i18n.t("cli.help.context_db_desc"))
def db_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Specific version to index (release, prerelease), or 'all'.")] = None,
) -> int:
    """Indexes the code into the DB (FTS5)."""
    root: Path = ctx.obj["root"]
    if version is not None and version != "all" and version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    
    versions_to_index = _resolve_context_versions(root, version, default_to_all=False)
    if not versions_to_index:
        out.error(i18n.t("cli.decompile.no_jar"))
        return 1

    for v in versions_to_index:
        #_ Removed nested out.status
        ok, payload = extractor.run_index(root, v)
        if ok:
            classes, methods, constants = payload
            out.success(i18n.t("cli.index.success", classes=classes, methods=methods, constants=constants, version=v))
        elif payload != "no_decompiled":
            out.error(i18n.t("cli.index.db_error"))
            return 1
    return 0


@app.command(name="list", help=i18n.t("cli.help.context_list_desc"))
def list_cmd(
    ctx: typer.Context
) -> int:
    """Lists indexed versions and shows the active one."""
    root: Path = ctx.obj["root"]
    provider = file_config.FileConfigProvider()
    
    with out.status(i18n.t("cli.context.list.loading")):
        ctx_list = get_context_list(provider, root)

    installed = ctx_list["indexed"]
    active = ctx_list["active"]
    
    if not installed:
        out.phase(i18n.t("cli.context.list.none"))
        return 0

    table_data = []
    for v in VALID_SERVER_VERSIONS:
        if v in installed:
            is_active = "✔" if v == active else ""
            table_data.append({"version": v, "active": is_active})

    out.table(
        title=i18n.t("cli.context.list.title"),
        data=table_data,
        columns=["version", "active"]
    )
    return 0


@app.command(name="use", help=i18n.t("cli.help.context_use_desc"))
def use_cmd(
    ctx: typer.Context,
    version_str: Annotated[str, typer.Argument(help="Version to set as active (release, prerelease).")]
) -> int:
    """Sets the active version (release or prerelease)."""
    root: Path = ctx.obj["root"]
    version = version_str.strip().lower()
    if version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    cfg = config_impl.load_config(root)
    cfg[config_impl.CONFIG_KEY_ACTIVE_SERVER] = version
    config_impl.save_config(cfg, root)
    if not config_impl.get_db_path(root, version).is_file():
        out.error(i18n.t("cli.context.use.not_indexed", version=version))
    out.success(i18n.t("cli.context.use.success", version=version))
    return 0


# The run_context function is removed because Typer handles dispatching.
