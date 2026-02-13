# src/prism/infrastructure/prune.py
#? Pruning: copies only com.hypixel.hytale from decompiled_raw to decompiled.

import sys
import shutil
from pathlib import Path

#_ from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from . import config_impl
from ..entrypoints.cli import out

#_ Subdirectories where decompilers may leave sources (version-dependent)
PRUNE_SOURCE_CANDIDATES = (
    "sources",  #_ Some engines use -d and write to <out>/sources/
    "",        #_ Or directly in the -d root
)


def prune_to_core(raw_dir: Path, dest_dir: Path) -> tuple[bool, dict | None]:
    """
    Copies only the core packages from raw_dir to dest_dir.
    Packages are defined in config_impl.CORE_PACKAGE_PATHS.
    Returns (True, {"files": N, "source_subdir": "sources"|"."}) or (False, None) if not found.
    """
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    found_any = False
    total_files = 0
    detected_subdir = "."

    with out.progress() as progress:
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
                
                task = progress.add_task(f"[cyan]Pruning {core_rel}", total=len(all_files), filename="")
                
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
    Runs only the pruning: copies com/hypixel/hytale from decompiled_raw/<version> to decompiled/<version>.
    Returns (True, "") or (False, "no_raw"|"prune_failed").
    """
    from .. import i18n
    from ..entrypoints.cli import out

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
    Runs only the pruning for one or more versions.
    If versions is None, it processes those that have an existing decompiled_raw folder.
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
