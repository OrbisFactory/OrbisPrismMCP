# config set game_path command.

import sys
from pathlib import Path
import argparse # NEW IMPORT

from ... import i18n
from ...infrastructure import config_impl
from ...infrastructure import detection


def cmd_config_set_jar_path(path_str: str, root: Path | None = None) -> int:
    """Sets the path to HytaleServer.jar or to the Hytale root folder."""
    root = root or config_impl.get_project_root()
    path = Path(path_str).resolve()
    cfg = config_impl.load_config(root)

    if path.is_dir() and detection.is_hytale_root(path):
        release_jar, prerelease_jar = detection.find_jar_paths_from_hytale_root(path)
        if not release_jar and not prerelease_jar:
            print(i18n.t("cli.config.jar_set_invalid", path=path_str), file=sys.stderr)
            return 1
        if release_jar:
            cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(release_jar.resolve())
            if prerelease_jar:
                cfg[config_impl.CONFIG_KEY_JAR_PATH_PRERELEASE] = str(prerelease_jar.resolve())
        else:
            cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(prerelease_jar.resolve())
        config_impl.save_config(cfg, root)
        print(i18n.t("cli.config.hytale_root_detected"))
        if release_jar:
            print(i18n.t("cli.init.success_jar", path=release_jar))
        if prerelease_jar:
            print(i18n.t("cli.init.sibling_saved", path=prerelease_jar))
        return 0
    if not detection.is_valid_jar(path):
        print(i18n.t("cli.config.jar_set_invalid", path=path_str), file=sys.stderr)
        return 1
    cfg[config_impl.CONFIG_KEY_JAR_PATH] = str(path)
    sibling = detection.get_sibling_version_jar_path(path)
    if sibling:
        if "pre-release" in str(path).replace("\\", "/"):
            cfg[config_impl.CONFIG_KEY_JAR_PATH_RELEASE] = str(sibling.resolve())
        else:
            cfg[config_impl.CONFIG_KEY_JAR_PATH_PRERELEASE] = str(sibling.resolve())
    config_impl.save_config(cfg, root)
    print(i18n.t("cli.config.jar_set_success", path=path))
    if sibling:
        print(i18n.t("cli.init.sibling_saved", path=sibling))
    return 0


def run_config(args: argparse.Namespace, root: Path) -> int:
    """Dispatch of the config command (set game_path)."""
    if args.config_impl_command == "set":
        if args.key == "game_path":
            return cmd_config_set_jar_path(args.value, root)
        else:
            print(i18n.t("cli.config.unknown_key", key=args.key), file=sys.stderr)
            return 1
    print(i18n.t("cli.unknown_command", cmd=f"config_impl {args.config_impl_command}"), file=sys.stderr)
    return 1
