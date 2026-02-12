# src/prism/application/ecs_service.py
from pathlib import Path
from ..ports.index_repository import IndexRepository

class ECSService:
    def __init__(self, repository: IndexRepository):
        self.repository = repository

    def find_systems_for_component(self, db_path: Path, component_name: str) -> list[dict]:
        """
        Searches for systems that process a specific component based on method parameters.
        Looks for classes with 'System' in the name having methods with the component in their parameters.
        """
        #_ 1. Search for classes ending in System or Systems
        systems_query = f"class_name:*System*"
        potential_systems = self.repository.search(db_path, systems_query, limit=100, unique_classes=True)
        
        found_systems = []
        for system in potential_systems:
            pkg = system["package"]
            cls = system["class_name"]
            
            #_ 2. Get class methods
            details = self.repository.get_class_and_methods(db_path, pkg, cls)
            if not details: continue
            
            #_ 3. Filter methods referencing the component in their parameters
            ref_methods = []
            for method in details.get("methods", []):
                params = method.get("params", "")
                if component_name in params:
                    ref_methods.append(method)
            
            if ref_methods:
                system_info = system.copy()
                system_info["methods"] = ref_methods
                found_systems.append(system_info)
                
        return found_systems
