
import os
import ast
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from ai_client import AIClient

# --- CONFIGURATION ---
WORKSPACE_DIR = "_agent_workspace"
REPO_MAP_FILE = "repo_map.json"
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '_agent_workspace'}
TARGET_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.rs', '.go', '.md'}
MAX_RETRIES = 3

# --- REPO CARTOGRAPHER CLASS ---
class RepoCartographer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.project_structure = {}

    def parse_python_ast(self, file_content: str) -> List[str]:
        try:
            tree = ast.parse(file_content)
            definitions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    definitions.append(f"Function: {node.name}({', '.join([a.arg for a in node.args.args])})")
                elif isinstance(node, ast.ClassDef):
                    definitions.append(f"Class: {node.name}")
            return definitions
        except SyntaxError:
            return ["(Parse Error)"]

    def map_repo(self) -> Dict:
        print(f"🗺️  Scanning codebase at: {self.root_path}")
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix not in TARGET_EXTENSIONS: continue

                rel_path = str(file_path.relative_to(self.root_path))
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    summary = self.parse_python_ast(content) if file_path.suffix == '.py' else ["(Non-Python File)"]

                    self.project_structure[rel_path] = {
                        "summary": summary,
                        "content_snippet": content[:500] + "..."
                    }
                except Exception as e:
                    print(f"⚠️  Skipping {rel_path}: {e}")

        with open(REPO_MAP_FILE, 'w') as f:
            json.dump(self.project_structure, f, indent=2)
        print(f"✅ Map saved to {REPO_MAP_FILE} ({len(self.project_structure)} files)")
        return self.project_structure


# --- SELF-HEALING AGENT ---
class SelfHealingAgent:
    def __init__(self):
        self.ai = AIClient()
        self.workspace = Path(WORKSPACE_DIR)
        self.workspace.mkdir(exist_ok=True)
        self.repo_map = {}

    def load_context(self):
        if not os.path.exists(REPO_MAP_FILE):
            mapper = RepoCartographer('.')
            self.repo_map = mapper.map_repo()
        else:
            with open(REPO_MAP_FILE, 'r') as f:
                self.repo_map = json.load(f)

    def write_to_workspace(self, filename: str, content: str):
        path = self.workspace / filename
        with open(path, "w") as f:
            f.write(content)
        return path

    def run_tests(self, test_file: str) -> Dict:
        print(f"   ⚙️ Executing {test_file}...")
        try:
            result = subprocess.run(
                ["python", test_file],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "Error: Test timed out."}
        except Exception as e:
            return {"success": False, "stderr": f"System Error: {str(e)}"}

    def execute_task(self, task: str):
        print(f"🚀 STARTING AUTONOMOUS AGENT: '{task}'")
        self.load_context()

        plan_prompt = f"Repo Map: {json.dumps(self.repo_map, indent=2)}\n\nTask: {task}. Return YAML plan."
        plan = self.ai.generate("Architect", plan_prompt)
        self.write_to_workspace("plan.yaml", plan)

        print("\n🏗️  Drafting Initial Solution...")
        solution_code = self.ai.generate("Python Dev", f"Plan: {plan}\nTask: {task}\nWrite the solution code.")
        self.write_to_workspace("solution.py", self._clean(solution_code))

        test_code = self.ai.generate("QA Engineer", f"Plan: {plan}\nTask: {task}\nWrite a pytest/unittest script named 'test_suite.py'.")
        self.write_to_workspace("test_suite.py", self._clean(test_code))

        attempt = 0
        while attempt < MAX_RETRIES:
            print(f"\n🔄 Attempt {attempt + 1}/{MAX_RETRIES}: Running Verification...")

            result = self.run_tests("test_suite.py")

            if result["success"]:
                print("   ✅ SUCCESS! Tests Passed.")
                print(f"   🎉 Final verified code is in {self.workspace}/solution.py")
                return

            else:
                print("   ❌ FAILED. Analyzing traceback...")
                error_msg = result["stderr"] if result["stderr"] else result["stdout"]
                print(f"   📝 Error Snippet: {error_msg[:200]}...")

                with open(self.workspace / 'solution.py', 'r') as f:
                    current_code = f.read()

                reflection_prompt = f"The previous code failed. Task: {task}\nCode:\n{current_code}\nError:\n{error_msg}\nRewrite the FULL 'solution.py' to fix the error."

                new_code = self.ai.generate("Senior Debugger", reflection_prompt)
                self.write_to_workspace("solution.py", self._clean(new_code))
                attempt += 1

        print("\n💀 MAX RETRIES REACHED. The agent could not solve the problem.")

    def _clean(self, text):
        return text.replace("```python", "").replace("```", "").strip()

# --- ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Agent for Software Engineering")
    parser.add_argument("task", type=str, help="The instruction (e.g., 'Refactor auth.py')")
    parser.add_argument("--remap", action="store_true", help="Force regeneration of the repo map")
    args = parser.parse_args()

    if args.remap and os.path.exists(REPO_MAP_FILE):
        os.remove(REPO_MAP_FILE)

    agent = SelfHealingAgent()
    agent.execute_task(args.task)
