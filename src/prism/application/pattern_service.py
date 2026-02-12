# src/prism/application/pattern_service.py
from pathlib import Path
from ..ports.index_repository import IndexRepository

class PatternService:
    def __init__(self, repository: IndexRepository):
        self.repository = repository

    def detect_patterns(self, db_path: Path, package: str, class_name: str) -> list[str]:
        """
        Analiza una clase y detecta patrones comunes.
        """
        details = self.repository.get_class_and_methods(db_path, package, class_name)
        if not details:
            return []
            
        patterns = []
        name = details["class_name"]
        methods = details.get("methods", [])
        constants = details.get("constants", [])
        
        #_ 1. Singleton detection
        has_get_instance = any(m["method"] in ["getInstance", "get"] and m["is_static"] for m in methods)
        has_static_instance = any(c["name"] in ["INSTANCE", "instance"] for c in constants)
        if has_get_instance or has_static_instance:
            patterns.append("Singleton")
            
        #_ 2. Factory detection
        is_factory_name = "Factory" in name
        has_create_method = any(m["method"] in ["create", "of", "from"] and m["is_static"] for m in methods)
        if is_factory_name or has_create_method:
            patterns.append("Factory")
            
        #_ 3. ECS System detection
        if "System" in name or any(m["method"] in ["onTick", "onEntityAdded", "onEntityRemoved"] for m in methods):
            patterns.append("ECS System")
            
        #_ 4. Component detection
        interfaces = details.get("interfaces", "") or ""
        if "Component" in name or "Component" in interfaces:
            patterns.append("ECS Component")
            
        #_ 5. Data/Value Object detection
        if not any(m["method"].startswith("set") for m in methods) and len(methods) > 0:
            if all(m["method"].startswith("get") or m["method"].startswith("is") or m["method"] in ["equals", "hashCode", "toString"] for m in methods):
                patterns.append("Immutable/Value Object")

        return patterns
