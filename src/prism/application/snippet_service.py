# src/prism/application/snippet_service.py
from pathlib import Path
from .read_source import read_source

class SnippetService:
    @staticmethod
    def get_snippet(config_provider, root, version, file_path, target_string, window=10) -> dict:
        """
        Reads a file and returns a code fragment around the first occurrence of target_string.
        """
        #_ Use existing function to read the full file
        data = read_source(config_provider, root, version, file_path)
        if "error" in data:
            return data
            
        content = data["content"]
        lines = content.splitlines()
        
        target_line_idx = -1
        for i, line in enumerate(lines):
            if target_string in line:
                target_line_idx = i
                break
                
        if target_line_idx == -1:
            return {"error": "not_found", "message": f"String '{target_string}' not found in file"}
            
        start = max(0, target_line_idx - window)
        end = min(len(lines), target_line_idx + window + 1)
        
        snippet = "\n".join(lines[start:end])
        
        return {
            "file_path": file_path,
            "version": version,
            "target": target_string,
            "start_line": start + 1,
            "end_line": end,
            "content": snippet
        }
