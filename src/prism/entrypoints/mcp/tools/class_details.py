# src/prism/entrypoints/mcp/tools/class_details.py
import json
from mcp.server.fastmcp import FastMCP
from .... import i18n
from ....application import (
    get_class as app_get_class,
    get_method as app_get_method,
    get_hierarchy as app_get_hierarchy,
)
from ....domain.constants import normalize_version
from ....ports.config_provider import ConfigProvider
from ....ports.index_repository import IndexRepository
from ..utils import parse_fqcn


def register(app: FastMCP, config: ConfigProvider, repository: IndexRepository):
    """Registers class details and hierarchy tools."""

    def prism_get_class(
        version: str,
        package: str | None = None,
        class_name: str | None = None,
        fqcn: str | None = None,
    ) -> str:
        norm_version = normalize_version(version)
        p = (package or "").strip()
        c = (class_name or "").strip()
        if (fqcn or "").strip():
            parsed = parse_fqcn(fqcn)
            if parsed:
                p, c = parsed
            else:
                c = fqcn.strip() # Treat as simple class name
        
        if not c:
            return json.dumps({"error": "missing_params", "message": "Provide class_name or fqcn."}, ensure_ascii=False)
        
        data, err = app_get_class(config, repository, None, norm_version, p, c)
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps({"version": norm_version, **data}, ensure_ascii=False)

    prism_get_class.__doc__ = i18n.t("mcp.tools.prism_get_class.description")
    app.tool()(prism_get_class)

    def prism_get_method(version: str, package: str, class_name: str, method_name: str) -> str:
        norm_version = normalize_version(version)
        if not (package or "").strip() or not (class_name or "").strip() or not (method_name or "").strip():
            return json.dumps({"error": "missing_params", "message": "package, class_name and method_name are required"}, ensure_ascii=False)
        data, err = app_get_method(config, repository, None, norm_version, package.strip(), class_name.strip(), method_name.strip())
        if err is not None:
            return json.dumps(err, ensure_ascii=False)
        return json.dumps({"version": norm_version, **data}, ensure_ascii=False)

    prism_get_method.__doc__ = i18n.t("mcp.tools.prism_get_method.description")
    app.tool()(prism_get_method)

    def prism_get_hierarchy(
        version: str,
        package: str | None = None,
        class_name: str | None = None,
        fqcn: str | None = None,
    ) -> str:
        norm_version = normalize_version(version)
        p = (package or "").strip()
        c = (class_name or "").strip()
        if (fqcn or "").strip():
            parsed = parse_fqcn(fqcn)
            if parsed:
                p, c = parsed
        if not p or not c:
            return json.dumps({"error": "missing_params", "message": "Provide package and class_name, or fqcn."}, ensure_ascii=False)
        
        data = app_get_hierarchy(config, norm_version, p, c, None)
        return json.dumps({"version": norm_version, **data}, ensure_ascii=False)

    prism_get_hierarchy.__doc__ = i18n.t("mcp.tools.prism_get_hierarchy.description")
    app.tool()(prism_get_hierarchy)
