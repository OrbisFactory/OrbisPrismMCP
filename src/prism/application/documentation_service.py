# src/prism/application/documentation_service.py
import json
from pathlib import Path

from .. import i18n
from ..infrastructure import config_impl

class DocumentationService:
    def __init__(self, resource_path: Path):
        self.resource_path = resource_path
        self._knowledge_bases = {} #_ Cache per language

    def _load_kb(self, locale: str):
        if locale not in self._knowledge_bases:
            kb_file = self.resource_path / f"knowledge.{locale}.json"
            if kb_file.exists():
                with open(kb_file, "r", encoding="utf-8") as f:
                    self._knowledge_bases[locale] = json.load(f)
            else:
                self._knowledge_bases[locale] = {}
        return self._knowledge_bases[locale]

    def explain_concept(self, concept: str, t=None) -> str:
        #_ Determine current locale
        root = config_impl.get_project_root()
        locale = i18n.get_current_locale(root)
        
        kb = self._load_kb(locale)
        
        #_ Try with main locale
        concept_upper = concept.upper()
        for key, value in kb.items():
            if key.upper() == concept_upper:
                return value
        
        #_ Try with fallback locale if different
        if locale != i18n.DEFAULT_LOCALE:
            fallback_kb = self._load_kb(i18n.DEFAULT_LOCALE)
            for key, value in fallback_kb.items():
                if key.upper() == concept_upper:
                    return value

        #? If not found, return a localized error message if translator is provided
        if t:
            return t("mcp.error.concept_not_found", concept=concept)
        return f"Concept '{concept}' not found in the local knowledge base. Use 'prism_search' to find related classes."
