# src/prism/infrastructure/decompile.py
#? Decompilation pipeline: JADX.

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

import time
import zipfile
#_ from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from . import config_impl
from . import jar_downloader
from . import prune
from ..entrypoints.cli import out


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


def run_jadx(
    jar_path: Path,
    out_dir: Path,
    jadx_jar: Path,
    log_path: Path | None = None,
) -> tuple[bool, bool]:
    """
    Runs JADX on the JAR and writes the output to out_dir.
    Returns (True, had_errors).
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    #_ JADX optimization: Use native threads for better performance
    cpu_cores = os.cpu_count() or 4
    
    #_ JVM + JADX Flags
    #_ -Xmx4G: Required for large Hytale class pools
    #_ -Djava.awt.headless=true: Force no-UI mode
    #_ -cp + JadxCLI: Explicitly bypass GUI entry point
    #_ --threads-count: Native parallelism
    #_ --show-bad-code: Fidelity
    #_ --no-res: Skip assets (faster)
    #_ --comments-level none: Cleaner source
    cmd = [
        "java",
        "-Xmx4G",
        "-Djava.awt.headless=true",
        "-XX:+UseParallelGC",
        "-cp", str(jadx_jar.resolve()),
        "jadx.cli.JadxCLI",
        str(jar_path.resolve()),
        "-d", str(out_dir.resolve()),
        "--threads-count", str(cpu_cores),
        "--show-bad-code",
        "--no-res",
        "--comments-level", "none",
    ]
    
    #_ Count total classes in JAR to have a progress target
    #_ JADX groups inner classes (with '$') into the main .java file.
    #_ By excluding them from the total, the progress bar will be much more accurate.
    total_classes = 0
    try:
        with zipfile.ZipFile(jar_path, 'r') as z:
            total_classes = sum(1 for f in z.namelist() if f.endswith(".class") and "$" not in f)
    except:
        total_classes = 1000 #_ Fallback
    
    start_time = time.time()
    try:
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"Command: {' '.join(cmd)}\n\n")

        with out.progress() as progress:
            task = progress.add_task("[cyan]Decompiling with JADX", total=total_classes, filename="")
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            
            #_ Monitoring loop to update progress bar based on files produced
            full_output = []
            while proc.poll() is None:
                #_ Count .java files in out_dir
                count = sum(1 for _ in out_dir.rglob("*.java"))
                progress.update(task, completed=count)
                
                #_ Non-blocking read of stdout
                line = proc.stdout.readline()
                if line:
                    full_output.append(line)
                
                time.sleep(1) #_ Check every second
            
            #_ Catch remaining output
            remaining = proc.stdout.read()
            if remaining:
                full_output.append(remaining)
            
            stdout = "".join(full_output)
            
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(stdout)
                    f.write(f"\n--- exit code: {proc.returncode} ---\n")

        elapsed = time.time() - start_time
        total_files = sum(1 for _ in out_dir.rglob("*.java"))
        
        return (True, {
            "had_errors": proc.returncode != 0,
            "total_files": total_files,
            "elapsed_time": elapsed
        })
    except Exception as e:
        print(f"JADX execution failed: {e}", file=sys.stderr)
        return (False, None)


def run_decompile_only_for_version(root: Path | None, version: str) -> tuple[bool, str | dict]:
    """
    Runs Vineflower only for a version. Returns (True, stats_dict) or (False, err_key).
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

    jadx_jar = jar_downloader.ensure_jadx(root)
    if not jadx_jar:
        return (False, "no_jadx")

    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config_impl.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{version}_{timestamp}.log"

    from .. import i18n
    ok, stats = run_jadx(jar_path, raw_dir, jadx_jar, log_path)
    if not ok:
        return (False, "decompile_failed")
    
    return (True, stats)


def run_decompile_only(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str | list[dict]]:
    """Runs JADX only (without pruning)."""
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [config_impl.get_active_version(root)]
    
    all_stats = []
    for version in versions:
        ok, result = run_decompile_only_for_version(root, version)
        if not ok:
            return (False, result)
        all_stats.append(result)
    return (True, all_stats)


def run_decompile_and_prune_for_version(root: Path | None, version: str) -> tuple[bool, str | dict]:
    """Decompiles with JADX and prunes."""
    ok, result = run_decompile_only_for_version(root, version)
    if not ok:
        return (False, result)

    root = root or config_impl.get_project_root()
    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    decompiled_dir = config_impl.get_decompiled_dir(root, version)
    
    from . import i18n
    ok_prune, stats = prune.prune_to_core(raw_dir, decompiled_dir)
    if not ok_prune:
        print(i18n.t("cli.prune.no_core", raw_dir=raw_dir), file=sys.stderr)
        return (False, "prun_failed")
    
    #_ Return both decompile stats and prune stats if needed, but for now we focus on decompile
    return (True, result)


def run_decompile_and_prune(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str | list[dict]]:
    """Decompiles and prunes one or more versions using JADX."""
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [config_impl.get_active_version(root)]

    all_stats = []
    for version in versions:
        ok, result = run_decompile_and_prune_for_version(root, version)
        if not ok:
            return (False, result)
        all_stats.append(result)
    return (True, all_stats)
