# Poda: copia solo com.hypixel.hytale desde decompiled_raw a decompiled.

import sys
import shutil
from pathlib import Path

from . import config

# Subdirectorios donde JADX puede dejar las fuentes (según versión)
PRUNE_SOURCE_CANDIDATES = (
    "sources",  # Muchas versiones de JADX usan -d y escriben en <out>/sources/
    "",        # O directamente en la raíz de -d
)


def prune_to_core(raw_dir: Path, dest_dir: Path) -> tuple[bool, dict | None]:
    """
    Copia solo la rama com/hypixel/hytale desde raw_dir a dest_dir.
    Prueba raw_dir/sources/com/hypixel/hytale y raw_dir/com/hypixel/hytale.
    Devuelve (True, {"files": N, "source_subdir": "sources"|"."}) o (False, None) si no existe.
    """
    core_rel = config.CORE_PACKAGE_PATH  # "com/hypixel/hytale"
    source_core = None
    source_subdir = None
    for sub in PRUNE_SOURCE_CANDIDATES:
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
