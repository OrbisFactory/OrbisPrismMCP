# src/prism/infrastructure/decompile.py
#? Decompilation pipeline: Vineflower.

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import config_impl
from . import jar_downloader
from . import prune


def check_java() -> bool:
    """Checks if 'java' is available in the PATH and is at least version 17."""
    java_bin = shutil.which("java")
    if not java_bin:
        return False
    try:
        #_ We just check if it runs. Vineflower needs Java 17 for Hytale bytecode usually.
        result = subprocess.run([java_bin, "-version"], capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def run_vineflower(
    jar_path: Path,
    out_dir: Path,
    vineflower_jar: Path,
    log_path: Path | None = None,
) -> tuple[bool, bool]:
    """
    Runs Vineflower on the JAR and writes the output to out_dir.
    Returns (True, had_errors).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    #_ Vineflower flags for modern Java (Hytale):
    #_ -dgs=1: De-guarda of generics
    #_ -rsy=1: Re-synthesize members
    #_ -ind=4: Standard indentation
    cmd = [
        "java",
        "-jar", str(vineflower_jar.resolve()),
        "-dgs=1",
        "-rsy=1",
        "-ind=4",
        str(jar_path.resolve()),
        str(out_dir.resolve()),
    ]
    
    try:
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"Command: {' '.join(cmd)}\n\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            progress.add_task("[cyan]Decompiling with Vineflower", total=None)
            
            #_ Vineflower doesn't give granular progress like JADX easily via stdout without custom plugins
            #_ So we just wait for it to finish.
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            
            stdout, _ = proc.communicate()
            
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(stdout)
                    f.write(f"\n--- exit code: {proc.returncode} ---\n")

        return (True, proc.returncode != 0)
    except Exception as e:
        print(f"Vineflower execution failed: {e}", file=sys.stderr)
        return (False, False)


def run_decompile_only_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """
    Runs Vineflower only for a version. Returns (True, "") or (False, err_key).
    """
    root = root or config_impl.get_project_root()
    if version == "release":
        jar_path = config_impl.get_jar_path_release_from_config(root)
    else:
        jar_path = config_impl.get_jar_path_prerelease_from_config(root)
    
    if jar_path is None:
        return (False, "no_jar")

    if not check_java():
        return (False, "java_not_found")

    vineflower_jar = jar_downloader.ensure_vineflower(root)
    if not vineflower_jar:
        return (False, "no_vineflower")

    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config_impl.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{version}_{timestamp}.log"

    from .. import i18n
    ok, had_errors = run_vineflower(jar_path, raw_dir, vineflower_jar, log_path)
    if not ok:
        return (False, "decompile_failed")
    
    return (True, "")


def run_decompile_only(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str]:
    """Runs Vineflower only (without pruning)."""
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [config_impl.get_active_version(root)]
    
    for version in versions:
        ok, err = run_decompile_only_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")


def run_decompile_and_prune_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """Decompiles with Vineflower and prunes."""
    ok, err = run_decompile_only_for_version(root, version)
    if not ok:
        return (False, err)

    root = root or config_impl.get_project_root()
    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    decompiled_dir = config_impl.get_decompiled_dir(root, version)
    
    from . import i18n
    ok_prune, stats = prune.prune_to_core(raw_dir, decompiled_dir)
    if not ok_prune:
        print(i18n.t("cli.prune.no_core", raw_dir=raw_dir), file=sys.stderr)
        return (False, "prun_failed")
    
    print(i18n.t("cli.prune.done", files=stats["files"], dest=decompiled_dir, subdir=stats["source_subdir"]))
    return (True, "")


def run_decompile_and_prune(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str]:
    """Decompiles and prunes one or more versions using Vineflower."""
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [config_impl.get_active_version(root)]

    for version in versions:
        ok, err = run_decompile_and_prune_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")
