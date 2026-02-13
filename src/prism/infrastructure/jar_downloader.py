# src/prism/infrastructure/jar_downloader.py
#? Generic JAR downloader using standard urllib.

import sys
import urllib.request
import zipfile
import shutil
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
                task = progress.add_task(desc, total=total_size, filename="")
                
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


def ensure_jadx(root: Path | None = None) -> Path | None:
    """
    Ensures JADX-CLI Fat JAR is present in workspace/bin. Downloads and extracts from ZIP if missing.
    Returns Path to the JAR or None if failed.
    """
    root = root or config_impl.get_project_root()
    dest_jar = config_impl.get_jadx_jar_path(root)
    
    if dest_jar.is_file():
        return dest_jar
    
    url = config_impl.get_jadx_url()
    desc = i18n.t("cli.decompile.downloading")
    
    bin_dir = config_impl.get_bin_dir(root)
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    zip_path = bin_dir / f"jadx-{config_impl.JADX_VERSION}.zip"
    extracted = False
    
    #_ Clean old artifacts if any
    if zip_path.exists():
        zip_path.unlink()

    if download_jar(url, zip_path, desc):
        try:
            #_ Extract specific all-jar from zip
            with zipfile.ZipFile(zip_path, 'r') as zf:
                #_ JADX zip structure contains lib/jadx-<version>-all.jar
                all_jar_name = config_impl.JADX_JAR_NAME
                target_member = None
                for member in zf.namelist():
                    if member.endswith(f"/lib/{all_jar_name}") or member == f"lib/{all_jar_name}":
                        target_member = member
                        break
                
                if target_member:
                    #_ Extract it to bin/
                    with zf.open(target_member) as source, open(dest_jar, "wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted = True
                else:
                    print(f"Error: Could not find {all_jar_name} in JADX zip.")
        except Exception as e:
            print(f"Error extracting JADX: {e}")
        
        #_ Clean up zip after closing
        if zip_path.exists():
            zip_path.unlink()
        
        if extracted:
            return dest_jar
            
    return None
