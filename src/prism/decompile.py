# Pipeline de descompilación: JADX y poda a com.hypixel.hytale.

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import config
from . import detection


def run_jadx(
    jar_path: Path,
    out_dir: Path,
    jadx_bin: str | Path,
    log_path: Path | None = None,
) -> bool:
    """
    Ejecuta JADX sobre el JAR y escribe la salida en out_dir.
    Opción -d out_dir -m restructure para código legible.
    Si log_path se proporciona, se escribe stdout y stderr ahí.
    Devuelve True si el proceso termina con código 0.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(jadx_bin),
        "-d",
        str(out_dir.resolve()),
        "-m",
        "restructure",
        str(jar_path.resolve()),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"Command: {' '.join(cmd)}\n\n")
                f.write("--- stdout ---\n")
                f.write(result.stdout or "")
                f.write("\n--- stderr ---\n")
                f.write(result.stderr or "")
                f.write(f"\n--- exit code: {result.returncode} ---\n")
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        if log_path:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("JADX execution failed (timeout or error).\n")
        return False


def prune_to_core(raw_dir: Path, dest_dir: Path) -> None:
    """
    Copia solo la rama com/hypixel/hytale desde raw_dir a dest_dir.
    dest_dir queda con la estructura com/hypixel/hytale/...; el resto se descarta.
    """
    core_rel = config.CORE_PACKAGE_PATH  # "com/hypixel/hytale"
    source_core = raw_dir / core_rel
    if not source_core.is_dir():
        dest_dir.mkdir(parents=True, exist_ok=True)
        return
    target = dest_dir / core_rel
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_core, target)


def run_decompile_and_prune(root: Path | None = None) -> tuple[bool, str]:
    """
    Orquesta: obtiene JAR y JADX de config, ejecuta JADX a decompiled_raw,
    poda a decompiled. Devuelve (True, "") si todo bien, o (False, "no_jar"|"no_jadx"|"jadx_failed").
    """
    root = root or config.get_project_root()
    jar_path = config.get_jar_path_from_config(root)
    if jar_path is None:
        return (False, "no_jar")

    jadx_path = config.get_jadx_path_from_config(root)
    if jadx_path is None:
        jadx_path = detection.resolve_jadx_path(root)
    if jadx_path is None:
        return (False, "no_jadx")
    jadx_bin = Path(jadx_path)

    raw_dir = config.get_decompiled_raw_dir(root)
    decompiled_dir = config.get_decompiled_dir(root)
    raw_dir.mkdir(parents=True, exist_ok=True)
    decompiled_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{timestamp}.log"

    if not run_jadx(jar_path, raw_dir, jadx_bin, log_path):
        return (False, "jadx_failed")

    prune_to_core(raw_dir, decompiled_dir)
    return (True, "")
