# src/prism/entrypoints/mcp/tools/listing.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import list_classes as app_list_classes
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository


def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers the prism_list_classes tool."""

    def prism_list_classes(
        version: str,
        package_prefix: str,
        prefix_match: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        norm_version = normalize_version(version)
        p = (package_prefix or "").strip()
        if not p:
            return json.dumps({"error": "missing_param", "message": "package_prefix is required"}, ensure_ascii=False)
        limit = max(1, min(int(limit), 500)) if limit is not None else 100
        offset = max(0, int(offset)) if offset is not None else 0
        classes, err = app_list_classes(config, repository, None, norm_version, p, prefix_match=prefix_match, limit=limit, offset=offset)
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps({
            "version": norm_version,
            "package_prefix": p,
            "prefix_match": prefix_match,
            "count": len(classes),
            "classes": classes,
        }, ensure_ascii=False)

    prism_list_classes.__doc__ = i18n.t("mcp.tools.prism_list_classes.description")
    app.tool()(prism_list_classes)

    def prism_list_packages(
        version: str = "release",
        package_prefix: str | None = None,
    ) -> str:
        from ....application import list_packages as app_list_packages
        norm_version = normalize_version(version)
        packages, err = app_list_packages(config, repository, None, norm_version, package_prefix)
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps({
            "version": norm_version,
            "package_prefix": package_prefix,
            "count": len(packages),
            "packages": packages,
        }, ensure_ascii=False)

    prism_list_packages.__doc__ = i18n.t("mcp.tools.prism_list_packages.description")
    app.tool()(prism_list_packages)
