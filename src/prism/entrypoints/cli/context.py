# src/prism/entrypoints/cli/context.py
#? Comandos 'context' / 'ctx' para gestionar el workspace, con Typer.

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

#_ Creamos una sub-aplicación de Typer para los comandos 'context'
app = typer.Typer(help=i18n.t("cli.context.help"))

def _ensure_dirs(root: Path) -> None:
    """Asegura que los directorios del workspace, decompiled, db y logs existan."""
    config_impl.get_workspace_dir(root).mkdir(parents=True, exist_ok=True)
    (config_impl.get_workspace_dir(root) / "server").mkdir(parents=True, exist_ok=True)
    config_impl.get_decompiled_dir(root).mkdir(parents=True, exist_ok=True)
    config_impl.get_db_dir(root).mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)

def _cmd_init_logic(root: Path) -> int:
    """Lógica interna para detectar HytaleServer.jar y guardar la configuración."""
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
    jadx_path = detection.resolve_jadx_path(root)
    if jadx_path:
        cfg[config_impl.CONFIG_KEY_JADX_PATH] = jadx_path
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

def _resolve_context_versions(root: Path, version: str | None) -> list[str] | None:
    """Determina la lista de versiones a usar; None si no hay JAR configurado."""
    if version is not None and version != "all":
        return [version]
    versions = []
    if config_impl.get_jar_path_release_from_config(root):
        versions.append("release")
    if config_impl.get_jar_path_prerelease_from_config(root):
        versions.append("prerelease")
    if not versions and config_impl.get_jar_path_from_config(root):
        versions = ["release"]
    return versions if versions else None


@app.command(name="detect")
def detect_cmd(
    ctx: typer.Context
) -> int:
    """Detecta HytaleServer.jar y guarda la configuración."""
    root: Path = ctx.obj["root"]
    return _cmd_init_logic(root)


@app.command(name="init")
def init_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Versión específica a procesar (release, prerelease), o 'all'.")] = None,
    single_thread: Annotated[bool, typer.Option("--single-thread", "-st", help="Descompilar usando un solo hilo para reducir el uso de CPU.")] = False,
) -> int:
    """Pipeline completo: detecta, descompila, poda e indexa."""
    root: Path = ctx.obj["root"]
    
    if _cmd_init_logic(root) != 0:
        return 1
    versions_list = _resolve_context_versions(root, version)
    if not versions_list:
        out.error(i18n.t("cli.decompile.no_jar"))
        return 1

    out.phase(i18n.t("cli.build.phase_decompile"))
    out.phase(i18n.t("cli.decompile.may_take"))
    
    with out.status(i18n.t("cli.build.phase_decompile")):
        success, err = decompile.run_decompile_only(root, versions=versions_list, single_thread_mode=single_thread)
    
    if not success:
        out.error(i18n.t("cli.build.decompile_failed"))
        out.error(i18n.t(f"cli.decompile.{err}"))
        return 1
    out.phase(i18n.t("cli.build.phase_decompile_done"))

    with out.status(i18n.t("cli.prune.pruning")):
        success, err = prune.run_prune_only(root, versions=versions_list)

    if not success:
        out.error(i18n.t("cli.prune." + err))
        return 1
    out.phase(i18n.t("cli.prune.completed_all"))


    out.phase(i18n.t("cli.build.phase_index"))
    for v in versions_list:
        with out.status(i18n.t("cli.build.indexing_version", version=v)):
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


@app.command(name="clean")
def clean_cmd(
    ctx: typer.Context,
    target: Annotated[str, typer.Argument(help="Objetivo a limpiar: 'db' (solo bases de datos), 'build' (archivos decompilados), o 'all'.",
                                         rich_help_panel="Opciones de limpieza")],
) -> int:
    """Limpia artefactos del workspace (db, build, all)."""
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
        with out.status(i18n.t("cli.context.clean.cleaning_all")):
            workspace_cleanup.clean_db(root)
            workspace_cleanup.clean_build(root)
        out.success(i18n.t("cli.context.clean.all_done"))
        return 0
    out.error(i18n.t("cli.context.clean.usage"))
    return 1


@app.command(name="reset")
def reset_cmd(
    ctx: typer.Context
) -> int:
    """Reinicia el proyecto a cero: limpia db + build y elimina .prism.json."""
    root: Path = ctx.obj["root"]
    with out.status(i18n.t("cli.context.reset.reseting")):
        workspace_cleanup.reset_workspace(root)
    out.success(i18n.t("cli.context.reset.done"))
    return 0


@app.command(name="decompile")
def decompile_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Versión específica a descompilar (release, prerelease), o 'all'.")] = None,
    single_thread: Annotated[bool, typer.Option("--single-thread", "-st", help="Descompilar usando un solo hilo para reducir el uso de CPU.")] = False,
) -> int:
    """Solo JADX → decompiled_raw (sin podar)."""
    root: Path = ctx.obj["root"]
    versions = None if version is None else [version]
    if version == "all":
        versions = _resolve_context_versions(root, None)

    out.phase(i18n.t("cli.decompile.may_take"))
    with out.status(i18n.t("cli.decompile.decompiling")):
        success, err = decompile.run_decompile_only(root, versions=versions, single_thread_mode=single_thread)

    if success:
        out.success(i18n.t("cli.decompile.success"))
        return 0
    out.error(i18n.t(f"cli.decompile.{err}"))
    return 1


@app.command(name="prune")
def prune_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Versión específica a podar (release, prerelease), o 'all'.")] = None,
) -> int:
    """Solo poda (raw → decompiled)."""
    root: Path = ctx.obj["root"]
    versions = None if version is None else [version]
    if version == "all":
        versions = _resolve_context_versions(root, None)
    
    with out.status(i18n.t("cli.prune.pruning")):
        success, err = prune.run_prune_only(root, versions=versions)

    if success:
        if version:
            out.success(i18n.t("cli.prune.success", version=version))
        else:
            out.success(i18n.t("cli.prune.completed_all"))
        return 0
    out.error(i18n.t(f"cli.prune.{err}"))
    return 1


@app.command(name="db")
def db_cmd(
    ctx: typer.Context,
    version: Annotated[Optional[str], typer.Argument(help="Versión específica a indexar (release, prerelease).")] = None,
) -> int:
    """Indexa el código en la DB (FTS5)."""
    root: Path = ctx.obj["root"]
    if version is not None and version not in VALID_SERVER_VERSIONS:
        out.error(i18n.t("cli.context.use.invalid"))
        return 1
    
    versions_to_index = [version] if version else VALID_SERVER_VERSIONS

    for v in versions_to_index:
        with out.status(i18n.t("cli.build.indexing_version", version=v)):
            ok, payload = extractor.run_index(root, v)
        if ok:
            classes, methods, constants = payload
            out.success(i18n.t("cli.index.success", classes=classes, methods=methods, constants=constants, version=v))
        elif payload != "no_decompiled":
            out.error(i18n.t("cli.index.db_error"))
            return 1
    return 0


@app.command(name="list")
def list_cmd(
    ctx: typer.Context
) -> int:
    """Lista las versiones indexadas y muestra cuál está activa."""
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


@app.command(name="use")
def use_cmd(
    ctx: typer.Context,
    version_str: Annotated[str, typer.Argument(help="Versión a establecer como activa (release, prerelease).")]
) -> int:
    """Establece la versión activa (release o prerelease)."""
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


# La función run_context se elimina porque Typer se encarga del dispatching.