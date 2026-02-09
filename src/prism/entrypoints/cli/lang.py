# lang commands: list and set.

import sys
from pathlib import Path
import argparse # NEW IMPORT

from ... import i18n
from ...infrastructure import config_impl


def cmd_lang_list(root: Path | None = None) -> int:
    """Lists available languages and marks the current one."""
    root = root or config_impl.get_project_root()
    current = i18n.get_current_locale(root)
    locales = i18n.get_available_locales()
    print(i18n.t("lang.list.header"))
    for code, name in locales:
        if code == current:
            print(i18n.t("lang.list.current", code=code, name=name))
        else:
            print(i18n.t("lang.list.entry", code=code, name=name))
    return 0


def cmd_lang_set(lang_code: str, root: Path | None = None) -> int:
    """Changes the language saved in .prism.json."""
    root = root or config_impl.get_project_root()
    code = lang_code.strip().lower()
    if not code:
        print(i18n.t("lang.set.invalid", lang=lang_code), file=sys.stderr)
        return 1
    if not i18n.is_locale_available(code):
        print(i18n.t("lang.set.invalid", lang=code), file=sys.stderr)
        return 1
    cfg = config_impl.load_config(root)
    cfg[config_impl.CONFIG_KEY_LANG] = code
    config_impl.save_config(cfg, root)
    print(i18n.t("lang.set.success", lang=code))
    return 0


def run_lang(args: argparse.Namespace, root: Path) -> int:
    """Dispatch of the lang command (list | set)."""
    if args.lang_command == "list":
        return cmd_lang_list(root)
    elif args.lang_command == "set":
        return cmd_lang_set(args.lang_code, root)
    print(i18n.t("cli.unknown_command", cmd=f"lang {args.lang_command}"), file=sys.stderr)
    return 1
