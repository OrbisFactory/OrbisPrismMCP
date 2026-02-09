# context / ctx commands: detect, init, clean, reset, decompile, prune, db, list, use.

import argparse # NEW IMPORT
import os
import sys
from pathlib import Path

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

# from . import args as cli_args # REMOVED
from . import out


def _ensure_dirs(root: Path) -> None:
    """Ensures that workspace/server, decompiled, db and logs directories exist."""
    config_impl.get_workspace_dir(root).mkdir(parents=True, exist_ok=True)
    (config_impl.get_workspace_dir(root) / "server").mkdir(parents=True, exist_ok=True)
    config_impl.get_decompiled_dir(root).mkdir(parents=True, exist_ok=True)
    config_impl.get_db_dir(root).mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)


def cmd_init(root: Path | None = None) -> int:
    """
    Detects HytaleServer.jar, validates and saves config to .prism.json.
    Creates workspace directories if they don't exist.
    """
    root = root or config_impl.get_project_root()
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


def cmd_context_detect(root: Path | None = None) -> int:
    """Detects JAR and saves config (same logic as top-level init)."""
    return cmd_init(root)


def _resolve_context_versions(root: Path, version: str | None) -> list[str] | None:
    """Determines the list of versions to use; None if no JAR is configured."""
    if version is not None and version != "all": # Handle 'all' explicitly for versions
        return [version]
    versions = []
    if config_impl.get_jar_path_release_from_config(root):
        versions.append("release")
    if config_impl.get_jar_path_prerelease_from_config(root):
        versions.append("prerelease")
    if not versions and config_impl.get_jar_path_from_config(root):
        versions = ["release"]
    return versions if versions else None


def cmd_context_init(root: Path | None = None, version: str | None = None, single_thread_mode: bool = False) -> int:
    """Full pipeline: detect (always at start) → decompile (JADX only) → prune → db. version=None -> all."""
    root = root or config_impl.get_project_root()
    # Always run detect first (same as ctx detect) to ensure JAR and config are up to date.
    if cmd_init(root) != 0:
        return 1
    versions_list = _resolve_context_versions(root, version)
    if not versions_list:
        out.error(i18n.t("cli.decompile.no_jar"))
        return 1

    out.phase(i18n.t("cli.build.phase_decompile"))
    out.phase(i18n.t("cli.decompile.may_take"))
    
    with out.status(i18n.t("cli.build.phase_decompile")):
        success, err = decompile.run_decompile_only(root, versions=versions_list, single_thread_mode=single_thread_mode)
    
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


def cmd_context_clean(root: Path | None = None, target: str = "") -> int:
    """Cleans based on target: db | build | b | all."""
    root = root or config_impl.get_project_root()
    t = (target or "").strip().lower()

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


def cmd_context_reset(root: Path | None = None) -> int:
    """Resets the project to zero: clean db + build and removes .prism.json."""
    root = root or config_impl.get_project_root()
    with out.status(i18n.t("cli.context.reset.reseting")):
        workspace_cleanup.reset_workspace(root)
    out.success(i18n.t("cli.context.reset.done"))
    return 0


def cmd_context_decompile(root: Path | None = None, version: str | None = None, single_thread_mode: bool = False) -> int:
    """Only JADX → decompiled_raw (without prune). version=None -> all."""
    root = root or config_impl.get_project_root()
    versions = None if version is None else [version]
    if version == "all":
        versions = _resolve_context_versions(root, None) # Get all versions if 'all' is specified

    out.phase(i18n.t("cli.decompile.may_take"))
    with out.status(i18n.t("cli.decompile.decompiling")):
        success, err = decompile.run_decompile_only(root, versions=versions, single_thread_mode=single_thread_mode)

    if success:
        out.success(i18n.t("cli.decompile.success"))
        return 0
    out.error(i18n.t(f"cli.decompile.{err}"))
    return 1


def cmd_prune(root: Path | None = None, version: str | None = None) -> int:
    """Only prune (raw → decompiled). version=None -> all that have raw."""
    root = root or config_impl.get_project_root()
    versions = None if version is None else [version]
    if version == "all":
        versions = _resolve_context_versions(root, None) # Get all versions if 'all' is specified
    
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


def cmd_index(root: Path | None = None, version: str | None = None) -> int:
    """Indexes into the DB. version=None -> release and prerelease."""
    root = root or config_impl.get_project_root()
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

def cmd_context_list(root: Path | None = None) -> int:
    """Lists indexed versions and shows which one is active."""
    root = root or config_impl.get_project_root()
    provider = file_config.FileConfigProvider()
    
    with out.status(i18n.t("cli.context.list.loading")):
        ctx = get_context_list(provider, root)

    installed = ctx["indexed"]
    active = ctx["active"]
    
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


def cmd_context_use(version_str: str, root: Path | None = None) -> int:
    """Sets the active version (release or prerelease)."""
    root = root or config_impl.get_project_root()
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


def run_context(args: argparse.Namespace, root: Path) -> int:
    """Dispatch for the context | ctx command."""
    subcommand = args.ctx_command

    if subcommand == "detect":
        return cmd_context_detect(root)
    elif subcommand == "init":
        return cmd_context_init(root, version=args.version, single_thread_mode=args.single_thread)
    elif subcommand == "clean":
        return cmd_context_clean(root, target=args.target)
    elif subcommand == "reset":
        return cmd_context_reset(root)
    elif subcommand == "decompile":
        return cmd_context_decompile(root, version=args.version, single_thread_mode=args.single_thread)
    elif subcommand == "prune":
        return cmd_prune(root, version=args.version)
    elif subcommand == "db":
        return cmd_index(root, version=args.version)
    elif subcommand == "list":
        return cmd_context_list(root)
    elif subcommand == "use":
        return cmd_context_use(args.version_str, root)
    else:
        # This case should ideally not be reached due to required=True in argparse
        print(i18n.t("cli.unknown_command", cmd=f"context {subcommand}"), file=sys.stderr)
        return 1

