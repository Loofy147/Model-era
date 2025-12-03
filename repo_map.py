
import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- CONFIGURATION ---
# Best Practice: Explicitly define what constitutes "Signal" vs "Noise"
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', 'build', 'dist', '.idea', '.vscode'}
IGNORE_FILES = {'.DS_Store', 'poetry.lock', 'package-lock.json', '.gitignore'}
TARGET_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.h', '.rs', '.go'}

class RepoCartographer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.project_structure = {}

    def is_ignored(self, path: Path) -> bool:
        """Logic: Filter out infrastructure/binary noise to focus on Logic Fidelity."""
        for part in path.parts:
            if part in IGNORE_DIRS or part.startswith('.'):
                return True
        if path.name in IGNORE_FILES:
            return True
        return False

    def parse_python_ast(self, file_content: str) -> Dict[str, Any]:
        """
        Deep Research Application: Using Abstract Syntax Trees (AST).
        We don't just read the text; we extract the *intent* (Classes/Functions).
        """
        try:
            tree = ast.parse(file_content)
            definitions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract function name and docstring (The "Contract")
                    docstring = ast.get_docstring(node)
                    definitions.append({
                        "type": "function",
                        "name": node.name,
                        "args": [a.arg for a in node.args.args],
                        "doc": docstring[:100] + "..." if docstring else None
                    })
                elif isinstance(node, ast.ClassDef):
                    definitions.append({
                        "type": "class",
                        "name": node.name,
                        "doc": ast.get_docstring(node)
                    })

            return {"definitions": definitions}
        except SyntaxError:
            return {"error": "Syntax Error in parsing"}

    def map_repo(self):
        """Walks the directory and builds the Knowledge Graph nodes."""
        print(f"🗺️  Mapping Logic Structure for: {self.root_path}")

        for root, dirs, files in os.walk(self.root_path):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]

            for file in files:
                file_path = Path(root) / file
                if self.is_ignored(file_path):
                    continue

                if file_path.suffix not in TARGET_EXTENSIONS:
                    continue

                # Relative path for cleaner context
                rel_path = str(file_path.relative_to(self.root_path))

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    file_info = {
                        "size": len(content),
                        "extension": file_path.suffix,
                        "analysis": {}
                    }

                    # If Python, apply AST logic. If JS/Other, we would apply TreeSitter (simplified here)
                    if file_path.suffix == '.py':
                        file_info["analysis"] = self.parse_python_ast(content)

                    self.project_structure[rel_path] = file_info
                    print(f"   ✅ Processed: {rel_path}")

                except Exception as e:
                    print(f"   ❌ Error reading {rel_path}: {e}")

    def export_map(self, output_file="repo_map.json"):
        with open(output_file, 'w') as f:
            json.dump(self.project_structure, f, indent=2)
        print(f"\n🚀 Logic Map exported to {output_file}")
        print(f"📊 Total Files Analyzed: {len(self.project_structure)}")

# --- EXECUTION ---
# Replace '.' with the path to the project you want to analyze
if __name__ == "__main__":
    # For demonstration, we map the current directory
    mapper = RepoCartographer('.')
    mapper.map_repo()
    mapper.export_map()
