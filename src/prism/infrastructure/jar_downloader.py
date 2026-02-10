# src/prism/infrastructure/jar_downloader.py
#? Generic JAR downloader using standard urllib.

import sys
import urllib.request
from pathlib import Path

from . import config_impl
from ..entrypoints.cli import out

from .. import i18n


def download_jar(url: str, dest_path: Path, description: str | None = None) -> bool:
    """
    Downloads a JAR file from a URL to a destination path.
    Shows a rich progress bar.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")

    desc = description or i18n.t("cli.decompile.downloading")

    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.info().get("Content-Length", 0))
            
            with out.progress() as progress:
                task = progress.add_task(desc, total=total_size)
                
                with open(temp_path, "wb") as f:
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
        
        temp_path.replace(dest_path)
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"\nError downloading {url}: {e}", file=sys.stderr)
        return False


def ensure_vineflower(root: Path) -> Path | None:
    """Checks if Vineflower is available, downloads it if not."""
    from . import config_impl
    
    path = config_impl.get_vineflower_path_from_config(root)
    if path and path.is_file():
        return path
    
    #_ Not found, let's download to workspace/bin
    dest = config_impl.get_workspace_dir(root) / "bin" / config_impl.VINEFLOWER_JAR_NAME
    url = config_impl.VINEFLOWER_DEFAULT_URL
    
    if download_jar(url, dest, i18n.t("cli.decompile.downloading")):
        return dest
    return None
