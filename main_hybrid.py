import os
import sys
import ast
import json
import yaml
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# --- LIBRARY: LiteLLM (The Gateway) ---
try:
    from litellm import completion
    import litellm
    # Suppress verbose LiteLLM logs
    litellm.suppress_instrumentation = True
except ImportError:
    print("❌ Critical: 'litellm' not found. Run: pip install litellm")
    sys.exit(1)

# --- CONFIGURATION ---
WORKSPACE_DIR = "_agent_workspace"
REPO_MAP_FILE = "repo_map.json"
MAX_RETRIES = 3

# MODEL ROSTER (Adjust based on your availability)
# Tier 1: High Intelligence, High Cost
MODEL_ARCHITECT = "gpt-4o"
# Tier 2: High Skill, Zero/Low Cost (Local or Cheap API)
# Use "ollama/qwen2.5-coder:14b" if running locally, or "gpt-4o-mini" / "groq/..."
MODEL_CODER = "ollama/qwen2.5-coder:14b"
# Tier 3: Fast, Zero Cost
MODEL_CLERK = "ollama/llama3.2"

# Fallback: If local models fail, use this cheap cloud model
MODEL_FALLBACK = "gpt-4o-mini"

# --- 1. HYBRID AI CLIENT (The Orchestrator) ---
class HybridAIClient:
    def __init__(self):
        self.check_local_availability()

    def check_local_availability(self):
        """Checks if Ollama is running if we are using it."""
        if "ollama" in MODEL_CODER:
            try:
                import requests
                response = requests.get("http://localhost:11434/")
                if response.status_code == 200:
                    print(f"🟢 Local Inference Engine (Ollama) is ONLINE.")
                else:
                    print(f"🟠 Ollama reachable but status {response.status_code}. Using Fallback.")
                    self._switch_to_fallback()
            except:
                print(f"🟠 Local Inference Engine (Ollama) NOT found. Switching to Cloud Reserve ({MODEL_FALLBACK}).")
                self._switch_to_fallback()

    def _switch_to_fallback(self):
        global MODEL_CODER, MODEL_CLERK
        MODEL_CODER = MODEL_FALLBACK
        MODEL_CLERK = MODEL_FALLBACK

    def generate(self, role: str, system_prompt: str, user_prompt: str) -> str:
        """
        Routes the prompt to the correct model based on Cognitive Load.
        """
        # Routing Logic
        if role in ["Architect", "Planner", "Auditor"]:
            model = MODEL_ARCHITECT
            temp = 0.1
        elif role in ["Python Dev", "QA Engineer", "Debugger"]:
            model = MODEL_CODER
            temp = 0.2
        else:
            model = MODEL_CLERK
            temp = 0.0

        print(f"   🧠 [Hybrid] Routing '{role}' -> {model}...")

        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temp,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"   ⚠️  Error with {model}: {e}")
            if model != MODEL_FALLBACK:
                print(f"   🔄 Retrying with Fallback ({MODEL_FALLBACK})...")
                try:
                    return completion(
                        model=MODEL_FALLBACK,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
                    ).choices[0].message.content
                except Exception as e2:
                    return f"Error: {e2}"
            return f"Error: {e}"

# --- 2. REPO CARTOGRAPHER (The Map) ---
class RepoCartographer:
    def __init__(self, root_path="."):
        self.root = Path(root_path)
        self.ignore = {'.git', '__pycache__', 'node_modules', 'venv', '_agent_workspace', '.env'}

    def map_repo(self):
        print("🗺️  Mapping codebase structure...")
        structure = {}
        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.ignore]
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.md')):
                    path = Path(root) / file
                    rel_path = str(path.relative_to(self.root))
                    try:
                        with open(path, 'r', errors='ignore') as f:
                            content = f.read()
                        # Simple summary for context efficiency
                        summary = self._summarize(content, path.suffix)
                        structure[rel_path] = summary
                    except: pass

        with open(REPO_MAP_FILE, 'w') as f:
            json.dump(structure, f, indent=2)
        return structure

    def _summarize(self, content, suffix):
        if suffix == '.py':
            try:
                tree = ast.parse(content)
                defs = [f"Function: {n.name}" for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                classes = [f"Class: {n.name}" for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                return defs + classes
            except: return ["(Parse Error)"]
        return ["(File Content)"]

# --- 3. GIT GATEKEEPER (The Safety) ---
class GitGatekeeper:
    def __init__(self):
        self.repo = Path(".")

    def run(self, args):
        return subprocess.run(["git"] + args, cwd=self.repo, capture_output=True, text=True).stdout.strip()

    def create_branch(self, task):
        clean_task = "".join([c if c.isalnum() else "-" for c in task]).lower()[:20]
        branch = f"agent/{clean_task}-{datetime.now().strftime('%H%M')}"

        # Stash if dirty
        if self.run(["status", "--porcelain"]):
            self.run(["stash", "save", "Agent-Safety-Stash"])

        self.run(["checkout", "-b", branch])
        print(f"🌿 Created branch: {branch}")
        return branch

    def commit(self, message):
        self.run(["add", "."])
        self.run(["commit", "-m", f"Agent: {message}"])

# --- 4. FLOW ENGINEER (The Agentic Loop) ---
class FlowEngineer:
    def __init__(self):
        self.ai = HybridAIClient()
        self.workspace = Path(WORKSPACE_DIR)
        self.workspace.mkdir(exist_ok=True)
        self.load_map()

    def load_map(self):
        if not os.path.exists(REPO_MAP_FILE):
            RepoCartographer().map_repo()
        with open(REPO_MAP_FILE) as f:
            self.map = json.load(f)

    def write_file(self, filename, content):
        clean_content = content.replace("```python", "").replace("```", "").strip()
        with open(self.workspace / filename, "w") as f:
            f.write(clean_content)

    def execute(self, task, target_file):
        print(f"\n🚀 STARTED Hybrid Agent on: {target_file}")

        # 1. ARCHITECT: Plan
        plan_prompt = f"Repo Map: {str(self.map)[:4000]}\nTarget: {target_file}\nTask: {task}\nCreate a YAML execution plan."
        plan = self.ai.generate("Architect", "You are a Senior Software Architect.", plan_prompt)
        self.write_file("plan.yaml", plan)
        print("   ✅ Plan Created.")

        # 2. QA ENGINEER: Test Harness
        test_prompt = f"Plan: {plan}\nWrite a Python script 'repro_test.py' that reproduces the issue or validates the new feature. It MUST fail initially."
        test_code = self.ai.generate("QA Engineer", "You are a Test Engineer. Write strict tests.", test_prompt)
        self.write_file("repro_test.py", test_code)
        print("   ✅ Test Harness Created.")

        # 3. DEV & REFLEXION LOOP
        print("   🔄 Entering Reflexion Loop...")
        for i in range(MAX_RETRIES):
            # Write/Fix Code
            if i == 0:
                code_prompt = f"Plan: {plan}\nTest: {test_code}\nWrite the solution for {target_file}."
                context = "Initial Code Generation."
            else:
                code_prompt = f"Previous code failed tests.\nError: {error_log}\nFix the code."
                context = f"Fixing Attempt #{i+1}"

            solution = self.ai.generate("Python Dev", f"You are a Senior Python Dev. {context}", code_prompt)
            self.write_file("solution.py", solution)

            # Run Test
            res = subprocess.run(["python", "repro_test.py"], cwd=self.workspace, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                print(f"   🎉 SUCCESS! Tests Passed on attempt {i+1}.")
                # 4. CRITIC: Final Review
                critique = self.ai.generate("Auditor", "Check for security/style.", f"Code: {solution}")
                self.write_file("review.md", critique)
                return True
            else:
                print(f"   ❌ Test Failed. Retrying...")
                error_log = res.stderr + res.stdout

        print("   💀 Max retries reached.")
        return False

# --- 5. MAIN ENTRY POINT ---
def main():
    parser = argparse.ArgumentParser(description="Hybrid Neuro-Symbolic Agent")
    parser.add_argument("file", help="Target file to modify")
    parser.add_argument("instruction", help="Natural language instruction")
    parser.add_argument("--remap", action="store_true", help="Force regenerate repo map")
    args = parser.parse_args()

    if args.remap: os.remove(REPO_MAP_FILE)

    # Initialize System
    git = GitGatekeeper()
    current_branch = git.run(["rev-parse", "--abbrev-ref", "HEAD"])

    try:
        # Create Sandbox Branch
        branch = git.create_branch(args.instruction)

        # Run Logic
        engine = FlowEngineer()
        success = engine.execute(args.instruction, args.file)

        if success:
            # Move from Sandbox to Real Repo
            src = Path(WORKSPACE_DIR) / "solution.py"
            dst = Path(args.file)
            shutil.copy(src, dst)
            print(f"   🚚 Transplanted solution to {dst}")

            git.commit(args.instruction)
            print(f"\n✨ DONE. Review changes: git diff {current_branch}..{branch}")
        else:
            print("\n❌ Task Failed. Reverting branch.")
            git.run(["checkout", current_branch])
            git.run(["branch", "-D", branch])

    except KeyboardInterrupt:
        print("\n🛑 Aborted by user.")
        git.run(["checkout", current_branch])

if __name__ == "__main__":
    main()
