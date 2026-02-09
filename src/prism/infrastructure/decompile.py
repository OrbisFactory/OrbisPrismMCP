# src/prism/infrastructure/decompile.py
#? Pipeline de descompilación: JADX.

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

#_ Línea de progreso de JADX, ej. "INFO  - progress: 44591 of 46688 (95%)"
JADX_PROGRESS_RE = re.compile(r"progress:\s*(\d+)\s+of\s+(\d+)\s+\((\d+)%\)")


def run_jadx(
    jar_path: Path,
    out_dir: Path,
    jadx_bin: str | Path,
    log_path: Path | None = None,
    single_thread_mode: bool = False,
) -> tuple[bool, bool]:
    """
    Ejecuta JADX en el JAR y escribe la salida en out_dir.
    Muestra una barra de progreso de Rich para las líneas de progreso de JADX; otras líneas (ej. errores) van a stderr.
    Si se proporciona log_path, cada línea se guarda en el archivo de log.
    Retorna (True, had_errors): True si terminó (incluso con errores); had_errors si el código de salida != 0.
    (False, False) si ocurrió una excepción (timeout, OSError).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    #_ Obtenemos el número de CPUs, con un fallback a 4 si no se puede detectar
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
            task = progress.add_task("[cyan]Descompilando", total=None)
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

        #_ Acepta la salida incluso si JADX reporta errores (común en JARs grandes); la poda usa lo que se generó
        return (True, proc.returncode != 0)
    except (subprocess.TimeoutExpired, OSError):
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("La ejecución de JADX falló (timeout o error).\n")
        return (False, False)


def run_decompile_only_for_version(root: Path | None, version: str, single_thread_mode: bool = False) -> tuple[bool, str]:
    """
    Ejecuta solo JADX para una versión (release o prerelease). No ejecuta la poda.
    Escribe en decompiled_raw/<version>. Retorna (True, "") o (False, "no_jar"|"no_jadx"|"jadx_failed").
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
    Ejecuta JADX solo (sin podar) para una o más versiones. Si versions es None, usa aquellas con un JAR configurado.
    Retorna (True, "") en éxito; (False, "no_jar"|"no_jadx"|"jadx_failed") en fallo.
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
    Descompila y poda una sola versión (release o prerelease).
    Retorna (True, "") o (False, "no_jar"|"no_jadx"|"jadx_failed").
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

    #_ Poda: raw -> decompiled (solo com.hypixel.hytale), con log
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
    Descompila y poda una o más versiones. Si versions es None, usa aquellas con JAR
    configurado (release y/o prerelease). Si no hay ninguno configurado, recurre a jar_path
    y descompila a release.
    Retorna (True, "") en éxito; (False, "no_jar"|"no_jadx"|"jadx_failed") en fallo.
    """
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = []
        if config_impl.get_jar_path_release_from_config(root):
            versions.append("release")
        if config_impl.get_jar_path_prerelease_from_config(root):
            versions.append("prerelease")
        if not versions:
            #_ Compatibilidad: un solo JAR en jar_path -> descompila a release
            if config_impl.get_jar_path_from_config(root):
                versions = ["release"]
            else:
                return (False, "no_jar")

    for version in versions:
        ok, err = run_decompile_and_prune_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")