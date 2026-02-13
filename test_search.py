# test_search.py
from src.prism.infrastructure import search_utils

queries = ["Block/Blocks", "com.hypixel.hytale.server", "hytale:stone", "Common/Blocks/Stone.json"]
for q in queries:
    print(f"Original: {q} -> Sanitized: {search_utils.sanitize_fts_query(q)}")
