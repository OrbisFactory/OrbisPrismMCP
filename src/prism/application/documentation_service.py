# src/prism/application/documentation_service.py
import json
from pathlib import Path

class DocumentationService:
    def __init__(self, resource_path: Path):
        self.resource_path = resource_path
        self._knowledge_base = None

    def _load_kb(self):
        if self._knowledge_base is None:
            kb_file = self.resource_path / "knowledge_base.json"
            if kb_file.exists():
                with open(kb_file, "r", encoding="utf-8") as f:
                    self._knowledge_base = json.load(f)
            else:
                self._knowledge_base = {}
        return self._knowledge_base

    def explain_concept(self, concept: str) -> str:
        kb = self._load_kb()
        #_ Búsqueda exacta e insensible a mayúsculas
        concept_upper = concept.upper()
        for key, value in kb.items():
            if key.upper() == concept_upper:
                return value
        
        #? Si no se encuentra, devolvemos una sugerencia genérica
        return f"Concepto '{concept}' no encontrado en la base de conocimientos local. Intenta buscar clases relacionadas con 'prism_search'."
