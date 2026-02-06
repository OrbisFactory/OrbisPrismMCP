# Pipeline de descompilación: JADX y poda a com.hypixel.hytale.

import sys
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
) -> tuple[bool, bool]:
    """
    Ejecuta JADX sobre el JAR y escribe la salida en out_dir.
    Muestra stdout/stderr en tiempo real; si log_path se da, lo guarda en el log.
    Devuelve (True, had_errors): True si terminó (aunque con errores); had_errors si exit code != 0.
    (False, False) si hubo excepción (timeout, OSError).
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

        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                if log_file:
                    log_file.write(line)
                    log_file.flush()
        finally:
            proc.wait(timeout=600)
            if log_file:
                log_file.write(f"\n--- exit code: {proc.returncode} ---\n")
                log_file.close()
        # Aceptamos salida aunque JADX reporte errores (común en JARs grandes); la poda usa lo generado
        return (True, proc.returncode != 0)
    except (subprocess.TimeoutExpired, OSError):
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("JADX execution failed (timeout or error).\n")
        return (False, False)


# Subdirectorios donde JADX puede dejar las fuentes (según versión)
_PRUNE_SOURCE_CANDIDATES = (
    "sources",  # Muchas versiones de JADX usan -d y escriben en <out>/sources/
    "",        # O directamente en la raíz de -d
)


def prune_to_core(raw_dir: Path, dest_dir: Path) -> tuple[bool, dict | None]:
    """
    Copia solo la rama com/hypixel/hytale desde raw_dir a dest_dir.
    Prueba raw_dir/sources/com/hypixel/hytale y raw_dir/com/hypixel/hytale.
    Devuelve (True, {"files": N, "source_subdir": "sources"|""}) o (False, None) si no existe.
    """
    core_rel = config.CORE_PACKAGE_PATH  # "com/hypixel/hytale"
    source_core = None
    source_subdir = None
    for sub in _PRUNE_SOURCE_CANDIDATES:
        candidate = (raw_dir / sub / core_rel) if sub else (raw_dir / core_rel)
        if candidate.is_dir():
            source_core = candidate
            source_subdir = sub or "."
            break
    if source_core is None:
        return (False, None)
    target = dest_dir / core_rel
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_core, target)
    # Contar solo archivos .java para el log
    file_count = sum(1 for _ in source_core.rglob("*.java"))
    return (True, {"files": file_count, "source_subdir": source_subdir})


def run_decompile_and_prune_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """
    Descompila y poda una sola versión (release o prerelease).
    Devuelve (True, "") o (False, "no_jar"|"no_jadx"|"jadx_failed").
    """
    root = root or config.get_project_root()
    if version == "release":
        jar_path = config.get_jar_path_release_from_config(root)
    else:
        jar_path = config.get_jar_path_prerelease_from_config(root)
    if jar_path is None:
        return (False, "no_jar")

    jadx_path = config.get_jadx_path_from_config(root)
    if jadx_path is None:
        jadx_path = detection.resolve_jadx_path(root)
    if jadx_path is None:
        return (False, "no_jadx")
    jadx_bin = Path(jadx_path)

    raw_dir = config.get_decompiled_raw_dir(root, version)
    decompiled_dir = config.get_decompiled_dir(root, version)
    raw_dir.mkdir(parents=True, exist_ok=True)
    decompiled_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = config.get_logs_dir(root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"decompile_{version}_{timestamp}.log"

    from . import i18n
    ok, had_errors = run_jadx(jar_path, raw_dir, jadx_bin, log_path)
    if not ok:
        return (False, "jadx_failed")
    if had_errors:
        print(i18n.t("cli.decompile.jadx_finished_with_errors"), file=sys.stderr)

    # Poda: raw -> decompiled (solo com.hypixel.hytale), con log
    ok_prune, stats = prune_to_core(raw_dir, decompiled_dir)
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
    Descompila y poda una o más versiones. Si versions es None, usa las que tengan JAR
    configurado (release y/o prerelease). Si ninguna está configurada, fallback a jar_path
    y descompila a release.
    Devuelve (True, "") si todo bien; (False, "no_jar"|"no_jadx"|"jadx_failed") si falla.
    """
    root = root or config.get_project_root()
    if versions is None:
        versions = []
        if config.get_jar_path_release_from_config(root):
            versions.append("release")
        if config.get_jar_path_prerelease_from_config(root):
            versions.append("prerelease")
        if not versions:
            # Compatibilidad: un solo JAR en jar_path → descompilar a release
            if config.get_jar_path_from_config(root):
                versions = ["release"]
            else:
                return (False, "no_jar")

    for version in versions:
        ok, err = run_decompile_and_prune_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")


def run_prune_only_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """
    Ejecuta solo la poda: copia com/hypixel/hytale desde decompiled_raw/<version> a decompiled/<version>.
    Devuelve (True, "") o (False, "no_raw"|"prune_failed").
    """
    from . import i18n

    root = root or config.get_project_root()
    raw_dir = config.get_decompiled_raw_dir(root, version)
    decompiled_dir = config.get_decompiled_dir(root, version)
    if not raw_dir.is_dir():
        return (False, "no_raw")
    print(i18n.t("cli.prune.running", version=version, raw_dir=raw_dir))
    ok, stats = prune_to_core(raw_dir, decompiled_dir)
    if not ok:
        print(i18n.t("cli.prune.no_core", raw_dir=raw_dir), file=sys.stderr)
        return (False, "prune_failed")
    print(i18n.t("cli.prune.done", files=stats["files"], dest=decompiled_dir, subdir=stats["source_subdir"]))
    return (True, "")


def run_prune_only(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Ejecuta solo la poda para una o más versiones.
    Si versions es None, procesa las que tengan carpeta decompiled_raw existente.
    """
    root = root or config.get_project_root()
    if versions is None:
        versions = [
            v for v in config.VALID_SERVER_VERSIONS
            if config.get_decompiled_raw_dir(root, v).is_dir()
        ]
        if not versions:
            return (False, "no_raw")
    for version in versions:
        ok, err = run_prune_only_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")
