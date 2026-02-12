# src/prism/application/ecs_service.py
from pathlib import Path
from ..ports.index_repository import IndexRepository

class ECSService:
    def __init__(self, repository: IndexRepository):
        self.repository = repository

    def find_systems_for_component(self, db_path: Path, component_name: str, limit: int = 100) -> list[dict]:
        """
        Searches for systems that process a specific component based on method parameters.
        """
        raw_results = self.repository.find_systems_for_component(db_path, component_name, limit)
        
        #_ Group by class
        systems = {}
        for row in raw_results:
            key = (row["package"], row["class_name"])
            if key not in systems:
                systems[key] = {
                    "package": row["package"],
                    "class_name": row["class_name"],
                    "file_path": row["file_path"],
                    "methods": []
                }
            systems[key]["methods"].append({
                "method": row["method"],
                "params": row["params"]
            })
            
        return list(systems.values())
