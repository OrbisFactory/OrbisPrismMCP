# src/prism/entrypoints/mcp/utils.py

def parse_fqcn(fqcn: str) -> tuple[str, str] | None:
    """Parses a Fully Qualified Class Name (FQCN) into package and class name."""
    s = (fqcn or "").strip()
    if not s or "." not in s:
        return None
    idx = s.rfind(".")
    return (s[:idx], s[idx + 1 :])
