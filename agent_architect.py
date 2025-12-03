
import os
import ast
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# --- 1. CONFIGURATION & SETUP ---
# Replace with your actual API Key environment variable handling
# os.environ["OPENAI_API_KEY"] = "sk-..."

# CONSTANTS
WORKSPACE_DIR = "_agent_workspace"
REPO_MAP_FILE = "repo_map.json"
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '_agent_workspace'}
TARGET_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.rs', '.go', '.md'}

# --- 2. THE MAPPER (RepoCartographer) ---
class RepoCartographer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.project_structure = {}

    def parse_python_ast(self, file_content: str) -> List[str]:
        """Extracts class/function signatures using AST."""
        try:
            tree = ast.parse(file_content)
            definitions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    definitions.append(f"Function: {node.name}({', '.join([a.arg for a in node.args.args])})")
                elif isinstance(node, ast.ClassDef):
                    definitions.append(f"Class: {node.name}")
            return definitions
        except Exception:
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

                    # AST parse for Python, lightweight summary for others
                    summary = self.parse_python_ast(content) if file_path.suffix == '.py' else ["(Non-Python File)"]

                    self.project_structure[rel_path] = {
                        "summary": summary,
                        "content_snippet": content[:500] + "..." # Truncated for context window efficiency
                    }
                except Exception as e:
                    print(f"⚠️  Skipping {rel_path}: {e}")

        # Save map
        with open(REPO_MAP_FILE, 'w') as f:
            json.dump(self.project_structure, f, indent=2)
        print(f"✅ Map saved to {REPO_MAP_FILE} ({len(self.project_structure)} files)")
        return self.project_structure

# --- 3. THE LLM CLIENT (Abstraction Layer) ---
class AIClient:
    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI() # Assumes OPENAI_API_KEY is set
            self.model = "gpt-4o"  # Or "gpt-4-turbo"
            self.available = True
        except ImportError:
            print("❌ OpenAI library not found. Run `pip install openai`.")
            self.available = False
        except Exception as e:
            print(f"❌ API Error: {e}")
            self.available = False

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.available:
            return " [MOCK OUTPUT: API Key Missing or Library not installed] "

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2 # Low temp for logic/code
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling API: {e}"

# --- 4. THE FLOW ENGINEER (Logic Core) ---
class FlowEngineer:
    def __init__(self):
        self.ai = AIClient()
        self.map_data = {}

        # Ensure workspace exists
        if not os.path.exists(WORKSPACE_DIR):
            os.makedirs(WORKSPACE_DIR)

    def load_context(self):
        if not os.path.exists(REPO_MAP_FILE):
            mapper = RepoCartographer('.')
            self.map_data = mapper.map_repo()
        else:
            with open(REPO_MAP_FILE, 'r') as f:
                self.map_data = json.load(f)

    def execute_task(self, task: str):
        print(f"\n🚀 STARTING AGENTIC WORKFLOW for: '{task}'")
        self.load_context()

        # --- Step 1: The Architect (Plan) ---
        print("\n🤔 Phase 1: Architecting Solution...")
        plan = self._step_plan(task)
        self._save_artifact("1_plan.yaml", plan)
        print(f"   -> Plan created. (See {WORKSPACE_DIR}/1_plan.yaml)")

        # --- Step 2: The QA Engineer (Test) ---
        print("\n🧪 Phase 2: Generating Test Harness...")
        test_code = self._step_test(task, plan)
        self._save_artifact("2_test_harness.py", test_code)
        print(f"   -> Test suite created. (See {WORKSPACE_DIR}/2_test_harness.py)")

        # --- Step 3: The Developer (Code) ---
        print("\n👨‍💻 Phase 3: Writing Implementation...")
        code = self._step_code(task, plan, test_code)
        self._save_artifact("3_solution.py", code)
        print(f"   -> Code generated. (See {WORKSPACE_DIR}/3_solution.py)")

        # --- Step 4: The Critic (Reflect) ---
        print("\n🧐 Phase 4: Auto-Reflection & Critique...")
        critique = self._step_critique(task, code)
        self._save_artifact("4_critique.txt", critique)
        print(f"   -> Critique finished.\n")

        print(f"✅ WORKFLOW COMPLETE. artifacts stored in '{WORKSPACE_DIR}/'")

    def _step_plan(self, task: str) -> str:
        system = "You are a Senior Software Architect. Analyze the repo map and request. Output a YAML plan."
        prompt = f"Repo Map: {str(self.map_data)[:10000]}\nTask: {task}\n\nReturn ONLY the YAML plan."
        return self.ai.generate(system, prompt)

    def _step_test(self, task: str, plan: str) -> str:
        system = "You are a QA Lead. Write a Python script to verify this plan. It must fail if the feature is missing."
        prompt = f"Plan: {plan}\nTask: {task}\n\nReturn ONLY valid Python code."
        return self._clean_code(self.ai.generate(system, prompt))

    def _step_code(self, task: str, plan: str, tests: str) -> str:
        system = "You are a Senior Python Dev. Write the code to satisfy the plan and pass the tests."
        prompt = f"Plan: {plan}\nTests: {tests}\n\nReturn ONLY valid Python code."
        return self._clean_code(self.ai.generate(system, prompt))

    def _step_critique(self, task: str, code: str) -> str:
        system = "You are a Security & Logic Auditor. Review the code for bugs, security issues, or deviations from the task."
        prompt = f"Task: {task}\nCode: {code}\n\nProvide a bullet-point critique."
        return self.ai.generate(system, prompt)

    def _clean_code(self, response: str) -> str:
        """Helper to strip markdown blocks if the LLM adds them."""
        return response.replace("```python", "").replace("```", "").strip()

    def _save_artifact(self, filename: str, content: str):
        path = os.path.join(WORKSPACE_DIR, filename)
        with open(path, 'w') as f:
            f.write(content)

# --- 5. CLI ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic Architect for Software Engineering")
    parser.add_argument("task", type=str, help="The instruction (e.g., 'Refactor auth.py')")
    parser.add_argument("--remap", action="store_true", help="Force regeneration of the repo map")

    args = parser.parse_args()

    if args.remap and os.path.exists(REPO_MAP_FILE):
        os.remove(REPO_MAP_FILE)

    engine = FlowEngineer()
    engine.execute_task(args.task)
