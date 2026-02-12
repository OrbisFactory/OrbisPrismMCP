# src/prism/entrypoints/mcp/tools/assets.py
import json
import base64
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application.assets_use_cases import AssetsUseCases
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.assets_repository import AssetsRepository
from ....infrastructure import config_impl

def register(app: FastMCP, config: ConfigProvider, repo: AssetsRepository):
    """Registers asset-related tools."""
    
    use_cases = AssetsUseCases(repo)

    def prism_search_assets(
        query: str,
        version: str = "release",
        limit: int = 30
    ) -> str:
        norm_version = normalize_version(version)
        db_path = config_impl.get_assets_db_path(None, norm_version)
        
        if not db_path.exists():
            return json.dumps({"error": "db_not_found", "message": f"Assets database for {norm_version} not found."}, ensure_ascii=False)
        
        results = use_cases.search_assets(db_path, query, limit)
        return json.dumps({
            "version": norm_version,
            "query": query,
            "count": len(results),
            "results": results
        }, ensure_ascii=False)

    def prism_inspect_asset(
        asset_path: str,
        version: str = "release"
    ) -> str:
        """Extracts the content of an asset. For text files returns string, for binary returns base64."""
        norm_version = normalize_version(version)
        assets_zip = config_impl.get_assets_zip_path(None, norm_version)
        
        if not assets_zip or not assets_zip.exists():
            return json.dumps({"error": "assets_not_found", "message": f"Assets.zip for {norm_version} not found."}, ensure_ascii=False)
        
        data = use_cases.inspect_asset_file(assets_zip, asset_path)
        if data is None:
            return json.dumps({"error": "asset_not_found", "message": f"Asset {asset_path} not found in {norm_version}."}, ensure_ascii=False)
        
        #_ Try to decode as UTF-8, if fails, return base64
        try:
            content = data.decode('utf-8')
            return json.dumps({"path": asset_path, "version": norm_version, "content": content, "encoding": "utf-8"}, ensure_ascii=False)
        except UnicodeDecodeError:
            b64 = base64.b64encode(data).decode('ascii')
            return json.dumps({"path": asset_path, "version": norm_version, "content": b64, "encoding": "base64"}, ensure_ascii=False)

    #_ Set descriptions from i18n
    prism_search_assets.__doc__ = "Search Hytale assets by path or metadata (JSON content). Returns matching files with path, extension and size."
    prism_inspect_asset.__doc__ = "Extracts the content of a specific asset from Assets.zip. Returns the content as a string if text or base64 if binary."
    
    app.tool()(prism_search_assets)
    app.tool()(prism_inspect_asset)
