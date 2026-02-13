# src/prism/infrastructure/search_utils.py
#? Utilities for FTS5 query sanitization and DSL parsing.

import re
from typing import Dict, List, Tuple

def sanitize_fts_query(query: str) -> str:
    """
    Sanitizes a query string for FTS5 to avoid syntax errors with special characters.
    1. Wraps terms with characters like /, :, - in double quotes.
    2. Handles dots (.) specially for FQCN (Package.Class) support.
    """
    if not query:
        return ""
    
    #_ Split by whitespace but keep phrases in quotes
    import re
    parts = re.findall(r'(?:"[^"]*"|\S+)', query)
    sanitized_parts = []
    
    for part in parts:
        #_ If already quoted, leave it
        if part.startswith('"') and part.endswith('"'):
            sanitized_parts.append(part)
            continue
            
        #_ If it contains a dot, it might be a FQCN or a package prefix
        if "." in part:
            if part.endswith(".*"):
                sanitized_parts.append(f'package:"{part[:-2]}*"')
                continue
                
            subparts = part.split(".")
            if len(subparts) > 1:
                last_part = subparts[-1]
                pkg_part = ".".join(subparts[:-1])
                
                #_ If last part starts with uppercase, it's likely Package.Class
                if last_part and last_part[0].isupper():
                    sanitized_parts.append(f'(package:"{pkg_part}" AND class_name:"{last_part}*")')
                else:
                    sanitized_parts.append(f'"{part}"')
            else:
                sanitized_parts.append(f'"{part}"')
        
        #_ If contains other special characters, wrap in double quotes
        elif any(c in part for c in "/:-"):
            safe_term = part.replace('"', '""')
            sanitized_parts.append(f'"{safe_term}"')
        else:
            sanitized_parts.append(part)
            
    return " ".join(sanitized_parts)

def parse_search_dsl(query: str) -> Tuple[str, Dict[str, str]]:
    """
    Parses a search string for DSL tokens like 'cat:Blocks' or 'ext:json'.
    Returns a tuple of (remaining_query, filters_dict).
    """
    filters = {}
    remaining_parts = []
    
    #_ Simple regex to find key:value patterns
    #_ Supports values without spaces. To support spaces, we'd need more complex logic.
    pattern = r'(\w+):([\w\:\.\/ \-]+)' #_ Basic version
    
    #_ Better approach: process words
    words = query.split()
    for word in words:
        if ':' in word and not any(word.lower().startswith(p) for p in ["http:", "https:"]):
            key, val = word.split(':', 1)
            filters[key.lower()] = val
        else:
            remaining_parts.append(word)
            
    return " ".join(remaining_parts), filters

def build_fts_query(user_query: str) -> str:
    """
    High-level entry point to convert user input to optimized FTS5 query.
    """
    clean_query, filters = parse_search_dsl(user_query)
    
    #_ For now, we only use the text part in FTS and filters are handled at DB level
    #_ In a more advanced version, we could inject filters into the FTS query
    #_ e.g., "category:Blocks stone"
    
    #_ Ensure we still have a query for FTS
    fts_term = sanitize_fts_query(clean_query or "*")
    
    return fts_term
