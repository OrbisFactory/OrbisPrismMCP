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


class DecompilerEngine:
    """Base class for decompiler engines."""
    def run(self, jar_path: Path, out_dir: Path, decompiler_jar: Path, log_path: Path | None = None) -> tuple[bool, dict | None]:
        raise NotImplementedError

    def create_slim_jar(self, input_jar: Path, output_jar: Path) -> bool:
        """Creates a temporary JAR containing only core Hytale packages."""
        #_ Optimization: Use cache if input JAR hasn't changed
        if output_jar.exists() and output_jar.stat().st_mtime > input_jar.stat().st_mtime:
            return True

        try:
            with zipfile.ZipFile(input_jar, 'r') as zin:
                #_ Use ZIP_STORED (no compression) for extreme speed. 
                #_ Compilers/Decompilers don't care, and we save CPU.
                with zipfile.ZipFile(output_jar, 'w', compression=zipfile.ZIP_STORED) as zout:
                    for item in zin.infolist():
                        #_ Only copy core packages (com/hypixel/hytale and com/hypixel/fastutil)
                        is_core = any(item.filename.startswith(p) for p in config_impl.CORE_PACKAGE_PATHS)
                        if is_core:
                            #_ writestr with ZIP_STORED is basically a byte copy.
                            zout.writestr(item, zin.read(item.filename))
            return True
        except Exception as e:
            print(f"Error creating slim JAR: {e}", file=sys.stderr)
            return False

class JadxEngine(DecompilerEngine):
    def run(self, jar_path: Path, out_dir: Path, decompiler_jar: Path, log_path: Path | None = None) -> tuple[bool, dict | None]:
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        cpu_cores = os.cpu_count() or 4
        cmd = [
            "java",
            "-Xmx4G",
            "-Djava.awt.headless=true",
            "-XX:+UseParallelGC",
            "-cp", str(decompiler_jar.resolve()),
            "jadx.cli.JadxCLI",
            str(jar_path.resolve()),
            "-d", str(out_dir.resolve()),
            "--threads-count", str(cpu_cores),
            "--show-bad-code",
            "--no-res",
            "--comments-level", "none",
        ]
        
        total_classes = 0
        try:
            with zipfile.ZipFile(jar_path, 'r') as z:
                total_classes = sum(1 for f in z.namelist() if f.endswith(".class") and "$" not in f)
        except:
            total_classes = 1000
        
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
                
                full_output = []
                while proc.poll() is None:
                    count = sum(1 for _ in out_dir.rglob("*.java"))
                    progress.update(task, completed=count)
                    
                    line = proc.stdout.readline()
                    if line:
                        full_output.append(line)
                    
                    time.sleep(1)
                
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

class VineflowerEngine(DecompilerEngine):
    def run(self, jar_path: Path, out_dir: Path, decompiler_jar: Path, log_path: Path | None = None) -> tuple[bool, dict | None]:
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        cpu_cores = os.cpu_count() or 4
        cmd = [
            "java",
            "-Xmx4G",
            "-jar", str(decompiler_jar.resolve()),
            f"--threads={cpu_cores}",
            "--rsy=1",
            "--dgs=1",
            str(jar_path.resolve()),
            str(out_dir.resolve()),
        ]
        
        total_classes = 0
        try:
            with zipfile.ZipFile(jar_path, 'r') as z:
                total_classes = sum(1 for f in z.namelist() if f.endswith(".class") and "$" not in f)
        except:
            total_classes = 1000
            
        start_time = time.time()
        try:
            if log_path:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"Command: {' '.join(cmd)}\n\n")

            with out.progress() as progress:
                task = progress.add_task("[magenta]Decompiling with Vineflower", total=total_classes, filename="")
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                
                full_output = []
                while proc.poll() is None:
                    count = sum(1 for _ in out_dir.rglob("*.java"))
                    progress.update(task, completed=count)
                    
                    line = proc.stdout.readline()
                    if line:
                        full_output.append(line)
                    
                    time.sleep(1)
                
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
            print(f"Vineflower execution failed: {e}", file=sys.stderr)
            return (False, None)

def get_engine(name: str) -> DecompilerEngine:
    if name.lower() == "vineflower":
        return VineflowerEngine()
    return JadxEngine()


def run_decompile_only_for_version(
    root: Path | None, 
    version: str, 
    engine_name: str | None = None
) -> tuple[bool, str | dict]:
    """
    Runs decompiler for a version. Returns (True, stats_dict) or (False, err_key).
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

    #_ Select engine
    engine_name = engine_name or config_impl.get_decompiler_engine_name(root)
    engine = get_engine(engine_name)
    
    #_ Ensure decompiler JAR
    if engine_name == "vineflower":
        decompiler_jar = jar_downloader.ensure_vineflower(root)
        err_key = "no_vineflower"
    else:
        decompiler_jar = jar_downloader.ensure_jadx(root)
        err_key = "no_jadx"
        
    if not decompiler_jar:
        return (False, err_key)

    raw_dir = config_impl.get_sources_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config_impl.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{engine_name}_{version}_{timestamp}.log"

    #_ 1. Create slim JAR
    slim_jar = raw_dir.parent / f"HytaleServer_{version}_slim.jar"
    if not engine.create_slim_jar(jar_path, slim_jar):
        return (False, "decompile_failed")

    ok, stats = engine.run(slim_jar, raw_dir, decompiler_jar, log_path)
    if not ok:
        return (False, "decompile_failed")
    return (True, stats)


def run_decompile_only(
    root: Path | None = None,
    versions: list[str] | None = None,
    engine_name: str | None = None
) -> tuple[bool, str | list[dict]]:
    """Runs decompiler only (without pruning)."""
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [config_impl.get_active_version(root)]
    
    all_stats = []
    for version in versions:
        ok, result = run_decompile_only_for_version(root, version, engine_name=engine_name)
        if not ok:
            return (False, result)
        all_stats.append(result)
    return (True, all_stats)


    return (True, all_stats)
