# src/prism/infrastructure/decompile.py
#? Decompilation pipeline: JADX.

import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from . import config_impl
from . import detection
from . import prune

#_ JADX progress line e.g. "INFO  - progress: 44591 of 46688 (95%)"
JADX_PROGRESS_RE = re.compile(r"progress:\s*(\d+)\s+of\s+(\d+)\s+\((\d+)%\)")


def run_jadx(
    jar_path: Path,
    out_dir: Path,
    jadx_bin: str | Path,
    log_path: Path | None = None,
    single_thread_mode: bool = False,
) -> tuple[bool, bool]:
    """
    Runs JADX on the JAR and writes the output to out_dir.
    Shows a Rich progress bar for JADX progress lines; other lines (e.g., errors) go to stderr.
    If log_path is provided, every line is saved to the log file.
    Returns (True, had_errors): True if it finished (even with errors); had_errors if the exit code != 0.
    (False, False) if an exception occurred (timeout, OSError).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    #_ Get the number of CPUs, with a fallback to 4 if it cannot be detected
    threads = 1 if single_thread_mode else (os.cpu_count() or 4)

    cmd = [
        str(jadx_bin),
        "--threads-count",
        str(threads),
        "-d",
        str(out_dir.resolve()),
        "-m",
        "restructure",
        str(jar_path.resolve()),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        log_file = None
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "w", encoding="utf-8")
            log_file.write(f"Command: {' '.join(cmd)}\n\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Decompiling", total=None)
            try:
                for line in proc.stdout:
                    if log_file:
                        log_file.write(line)
                        log_file.flush()
                    match = JADX_PROGRESS_RE.search(line)
                    if match:
                        current, total = int(match.group(1)), int(match.group(2))
                        if progress.tasks[task].total is None:
                            progress.update(task, total=total)
                        progress.update(task, completed=current)
                    else:
                        progress.console.print(line.strip())
            finally:
                proc.wait(timeout=600)
                if log_file:
                    log_file.write(f"\n--- exit code: {proc.returncode} ---\n")
                    log_file.close()

        #_ Accept the output even if JADX reports errors (common on large JARs); pruning uses what was generated
        return (True, proc.returncode != 0)
    except (subprocess.TimeoutExpired, OSError):
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("JADX execution failed (timeout or error).\n")
        return (False, False)


def run_decompile_only_for_version(root: Path | None, version: str, single_thread_mode: bool = False) -> tuple[bool, str]:
    """
    Runs JADX only for a version (release or prerelease). Does not run pruning.
    Writes to decompiled_raw/<version>. Returns (True, "") or (False, "no_jar"|"no_jadx"|"jadx_failed").
    """
    root = root or config_impl.get_project_root()
    if version == "release":
        jar_path = config_impl.get_jar_path_release_from_config(root)
    else:
        jar_path = config_impl.get_jar_path_prerelease_from_config(root)
    if jar_path is None:
        return (False, "no_jar")

    jadx_path = config_impl.get_jadx_path_from_config(root)
    if jadx_path is None:
        jadx_path = detection.resolve_jadx_path(root)
    if jadx_path is None:
        return (False, "no_jadx")
    jadx_bin = Path(jadx_path)

    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config_impl.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{version}_{timestamp}.log"

    from .. import i18n
    ok, had_errors = run_jadx(jar_path, raw_dir, jadx_bin, log_path, single_thread_mode=single_thread_mode)
    if not ok:
        return (False, "jadx_failed")
    if had_errors:
        print(i18n.t("cli.decompile.jadx_finished_with_errors"), file=sys.stderr)
    return (True, "")


def run_decompile_only(
    root: Path | None = None,
    versions: list[str] | None = None,
    single_thread_mode: bool = False,
) -> tuple[bool, str]:
    """
    Runs JADX only (without pruning) for one or more versions. If versions is None, uses those with a configured JAR.
    Returns (True, "") on success; (False, "no_jar"|"no_jadx"|"jadx_failed") on failure.
    """
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = []
        if config_impl.get_jar_path_release_from_config(root):
            versions.append("release")
        if config_impl.get_jar_path_prerelease_from_config(root):
            versions.append("prerelease")
        if not versions:
            if config_impl.get_jar_path_from_config(root):
                versions = ["release"]
            else:
                return (False, "no_jar")

    for version in versions:
        ok, err = run_decompile_only_for_version(root, version, single_thread_mode=single_thread_mode)
        if not ok:
            return (False, err)
    return (True, "")


def run_decompile_and_prune_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """
    Decompiles and prunes a single version (release or prerelease).
    Returns (True, "") or (False, "no_jar"|"no_jadx"|"jadx_failed").
    """
    root = root or config_impl.get_project_root()
    if version == "release":
        jar_path = config_impl.get_jar_path_release_from_config(root)
    else:
        jar_path = config_impl.get_jar_path_prerelease_from_config(root)
    if jar_path is None:
        return (False, "no_jar")

    jadx_path = config_impl.get_jadx_path_from_config(root)
    if jadx_path is None:
        jadx_path = detection.resolve_jadx_path(root)
    if jadx_path is None:
        return (False, "no_jadx")
    jadx_bin = Path(jadx_path)

    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    decompiled_dir = config_impl.get_decompiled_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)
    decompiled_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config_impl.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{version}_{timestamp}.log"

    from . import i18n
    ok, had_errors = run_jadx(jar_path, raw_dir, jadx_bin, log_path)
    if not ok:
        return (False, "jadx_failed")
    if had_errors:
        print(i18n.t("cli.decompile.jadx_finished_with_errors"), file=sys.stderr)

    #_ Pruning: raw -> decompiled (only com.hypixel.hytale), with log
    ok_prune, stats = prune.prune_to_core(raw_dir, decompiled_dir)
    if not ok_prune:
        print(i18n.t("cli.prune.no_core", raw_dir=raw_dir), file=sys.stderr)
        return (False, "prune_failed")
    print(i18n.t("cli.prune.done", files=stats["files"], dest=decompiled_dir, subdir=stats["source_subdir"]))
    return (True, "")


def run_decompile_and_prune(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Decompiles and prunes one or more versions. If versions is None, uses those with a configured JAR
    (release and/or prerelease). If none are configured, falls back to jar_path
    and decompiles to release.
    Returns (True, "") on success; (False, "no_jar"|"no_jadx"|"jadx_failed") on failure.
    """
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = []
        if config_impl.get_jar_path_release_from_config(root):
            versions.append("release")
        if config_impl.get_jar_path_prerelease_from_config(root):
            versions.append("prerelease")
        if not versions:
            #_ Compatibility: a single JAR in jar_path -> decompile to release
            if config_impl.get_jar_path_from_config(root):
                versions = ["release"]
            else:
                return (False, "no_jar")

    for version in versions:
        ok, err = run_decompile_and_prune_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")
