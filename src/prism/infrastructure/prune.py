# src/prism/infrastructure/prune.py
#? Poda: copia solo com.hypixel.hytale de decompiled_raw a decompiled.

import sys
import shutil
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from . import config_impl

#_ Subdirectorios donde JADX puede dejar los fuentes (depende de la versión)
PRUNE_SOURCE_CANDIDATES = (
    "sources",  #_ Muchas versiones de JADX usan -d y escriben en <out>/sources/
    "",        #_ O directamente en la raíz de -d
)


def prune_to_core(raw_dir: Path, dest_dir: Path) -> tuple[bool, dict | None]:
    """
    Copia solo los paquetes principales de raw_dir a dest_dir.
    Los paquetes se definen en config_impl.CORE_PACKAGE_PATHS.
    Retorna (True, {"files": N, "source_subdir": "sources"|"."}) o (False, None) si no se encuentra.
    """
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    found_any = False
    total_files = 0
    detected_subdir = "."

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        for core_rel in config_impl.CORE_PACKAGE_PATHS:
            source_core = None
            source_subdir = None
            for sub in PRUNE_SOURCE_CANDIDATES:
                candidate = (raw_dir / sub / core_rel) if sub else (raw_dir / core_rel)
                if candidate.is_dir():
                    source_core = candidate
                    source_subdir = sub or "."
                    break
            
            if source_core:
                found_any = True
                detected_subdir = source_subdir
                target = dest_dir / core_rel
                all_files = [p for p in source_core.rglob("*") if p.is_file()]
                
                task = progress.add_task(f"[cyan]Podando {core_rel}", total=len(all_files))
                
                for src in all_files:
                    rel = src.relative_to(source_core)
                    tgt = target / rel
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, tgt)
                    progress.update(task, advance=1)
                
                total_files += len(all_files)

    if not found_any:
        return (False, None)

    return (True, {"files": total_files, "source_subdir": detected_subdir})


def run_prune_only_for_version(root: Path | None, version: str) -> tuple[bool, str]:
    """
    Ejecuta solo la poda: copia com/hypixel/hytale de decompiled_raw/<version> a decompiled/<version>.
    Retorna (True, "") o (False, "no_raw"|"prune_failed").
    """
    from .. import i18n

    root = root or config_impl.get_project_root()
    raw_dir = config_impl.get_decompiled_raw_dir(root, version)
    decompiled_dir = config_impl.get_decompiled_dir(root, version)
    if not raw_dir.is_dir():
        return (False, "no_raw")
    
    ok, stats = prune_to_core(raw_dir, decompiled_dir)
    if not ok:
        out.error(i18n.t("cli.prune.no_core", raw_dir=raw_dir))
        return (False, "prune_failed")
    
    return (True, "")


def run_prune_only(
    root: Path | None = None,
    versions: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Ejecuta solo la poda para una o más versiones.
    Si versions es None, procesa aquellas que tengan una carpeta decompiled_raw existente.
    """
    root = root or config_impl.get_project_root()
    if versions is None:
        versions = [
            v for v in config_impl.VALID_SERVER_VERSIONS
            if config_impl.get_decompiled_raw_dir(root, v).is_dir()
        ]
        if not versions:
            return (False, "no_raw")
    for version in versions:
        ok, err = run_prune_only_for_version(root, version)
        if not ok:
            return (False, err)
    return (True, "")