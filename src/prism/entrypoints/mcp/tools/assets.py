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
        
        #_ search_assets now needs db_path
        results = use_cases.search_assets(db_path, query, limit)
        
        #_ Format results for better readability in MCP
        formatted = []
        for a in results:
            item = {
                "path": a.path,
                "category": a.category,
                "internal_id": a.internal_id,
                "extension": a.extension,
                "size_bytes": a.size
            }
            if a.width and a.height:
                item["dimensions"] = f"{a.width}x{a.height}"
            formatted.append(item)

        return json.dumps({
            "version": norm_version,
            "query": query,
            "count": len(formatted),
            "results": formatted
        }, ensure_ascii=False, indent=2)

    def prism_inspect_asset(
        asset_path: str,
        version: str = "release"
    ) -> str:
        """Extracts the content of an asset. For text files returns string, for binary returns base64."""
        norm_version = normalize_version(version)
        db_path = config_impl.get_assets_db_path(None, norm_version)
        
        #_ We get info from DB first to see metadata/category
        info = None
        if db_path.exists():
            info = use_cases.get_asset_info(db_path, asset_path)
        
        assets_zip = config_impl.get_assets_zip_path(None, norm_version)
        if not assets_zip or not assets_zip.exists():
             return json.dumps({"error": "assets_not_found", "message": f"Assets.zip for {norm_version} not found."}, ensure_ascii=False)

        data = use_cases.inspect_asset_file(assets_zip, asset_path)
        if data is None:
            return json.dumps({"error": "asset_not_found", "message": f"Asset {asset_path} not found in {norm_version}."}, ensure_ascii=False)
        
        result = {
            "path": asset_path,
            "version": norm_version,
            "category": info.category if info else None,
            "internal_id": info.internal_id if info else None,
        }
        
        if info and info.width and info.height:
            result["dimensions"] = f"{info.width}x{info.height}"

        #_ Try to decode as UTF-8, if fails, return base64
        try:
            content = data.decode('utf-8')
            
            #_ If content is too large (> 50KB), offer a summary/truncate
            if len(content) > 50000:
                result["content_summary"] = f"File is too large ({len(content)} bytes). Showing first 500 characters."
                result["content"] = content[:500] + "\n... [TRUNCATED] ..."
                result["is_truncated"] = True
            else:
                result["content"] = content
                
            result["encoding"] = "utf-8"
        except UnicodeDecodeError:
            b64 = base64.b64encode(data).decode('ascii')
            #_ base64 also truncated if too large
            if len(b64) > 100000:
                 result["content"] = b64[:1000] + "... [BASE64 TRUNCATED] ..."
                 result["is_truncated"] = True
            else:
                 result["content"] = b64
            result["encoding"] = "base64"
        
        return json.dumps(result, ensure_ascii=False, indent=2)

    #_ Set descriptions from i18n
    prism_search_assets.__doc__ = "Busca assets de Hytale por ruta, ID interno (en JSONs) o categoría (ej: Block, AmbienceFX). Retorna dimensiones para imágenes."
    prism_inspect_asset.__doc__ = "Inspecciona el contenido de un asset. Devuelve el contenido (texto o base64) junto con metadatos técnicos y categoría detectada."
    
    app.tool()(prism_search_assets)
    app.tool()(prism_inspect_asset)
