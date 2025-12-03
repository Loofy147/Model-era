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

# --- 4. MEMORY MANAGER (The Scribe) ---
class MemoryManager:
    def __init__(self, memory_file="agent_memory.json"):
        self.memory_file = Path(memory_file)
        self.memories = self._load_memories()

    def _load_memories(self):
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return []

    def save_experience(self, task: str, success: bool, solution: str):
        experience = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "success": success,
            "solution": solution,
        }
        self.memories.append(experience)
        with open(self.memory_file, 'w') as f:
            json.dump(self.memories, f, indent=2)
        print("   📝 Experience saved to memory.")

    def find_similar_experiences(self, task: str, top_k=2):
        # Simple keyword-based similarity for now.
        # A more advanced implementation would use embeddings.
        task_keywords = set(task.lower().split())

        scored_memories = []
        for mem in self.memories:
            mem_keywords = set(mem['task'].lower().split())
            score = len(task_keywords.intersection(mem_keywords))
            if score > 0:
                scored_memories.append({"score": score, "memory": mem})

        scored_memories.sort(key=lambda x: x['score'], reverse=True)
        return [item['memory'] for item in scored_memories[:top_k]]

# --- 5. FLOW ENGINEER (The Agentic Loop) ---
class FlowEngineer:
    def __init__(self):
        self.ai = HybridAIClient()
        self.memory = MemoryManager()
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

        # 1. RETRIEVE & PLAN: Architect and Validator Loop
        print("   🤝 Entering Planning Loop...")
        similar_experiences = self.memory.find_similar_experiences(task)
        experiential_context = "\n".join([f"- Task: {exp['task']}\n  Success: {exp['success']}\n  Solution:\n```python\n{exp['solution']}\n```" for exp in similar_experiences])

        system_prompt_architect = """
You are a Senior Software Architect. Your task is to create a detailed, multi-step execution plan.
Incorporate lessons from past experiences to improve your plan. A good plan is the most critical step to success.
Output the plan in a strict YAML format with `thought_process`, `edge_cases`, and `plan` sections.
"""
        system_prompt_validator = """
You are a Plan Validator. Your task is to review a YAML plan.
If the plan is logical, feasible, and detailed, respond with "APPROVED".
Otherwise, provide a brief, constructive critique.
"""
        plan = ""
        critique = ""
        for i in range(MAX_RETRIES):
            plan_prompt = f"Similar Past Experiences:\n{experiential_context}\n\nCodebase Map:\n{str(self.map)[:3000]}\n\nTarget: `{target_file}`\nRequest: \"{task}\"\nPrior Critique: {critique}\n\nGenerate or revise the YAML execution plan."
            plan = self.ai.generate("Architect", system_prompt_architect, plan_prompt)

            validation_prompt = f"Please validate this plan:\n\n---\n{plan}\n---"
            validation = self.ai.generate("Validator", system_prompt_validator, validation_prompt)

            if "APPROVED" in validation.upper():
                print(f"   ✅ Plan Approved on attempt {i+1}.")
                self.write_file("plan.yaml", plan)
                break
            else:
                critique = validation
                print(f"   🟠 Plan Rejected. Critique: {critique}")
        else:
            print("   💀 Max retries reached for planning. Aborting.")
            self.memory.save_experience(task, False, "") # Save failure
            return False

        # 2. QA ENGINEER: Test Harness
        test_prompt = f"Plan: {plan}\nWrite a Python script 'repro_test.py' that reproduces the issue or validates the new feature. It MUST fail initially."
        test_code = self.ai.generate("QA Engineer", "You are a Test Engineer. Write strict tests.", test_prompt)
        self.write_file("repro_test.py", test_code)
        print("   ✅ Test Harness Created.")

        # 3. DEV & REFLEXION LOOP
        print("   🔄 Entering Reflexion Loop...")
        solution = ""
        for i in range(MAX_RETRIES):
            # Write/Fix Code
            if i == 0:
                code_prompt = f"Similar Past Experiences:\n{experiential_context}\n\nPlan:\n{plan}\n\nTest Harness:\n{test_code}\n\nWrite the full code for `{target_file}` to pass the test."
                context = "Initial Code Generation."
            else:
                code_prompt = f"Similar Past Experiences:\n{experiential_context}\n\nYour previous code failed the tests.\nError:\n{error_log}\n\nTest Harness:\n{test_code}\n\nRewrite the full code for `{target_file}` to fix the error."
                context = f"Fixing Attempt #{i+1}"

            solution = self.ai.generate("Python Dev", f"You are a Senior Python Developer. {context}", code_prompt)
            self.write_file("solution.py", solution)

            # Run Test
            res = subprocess.run(["python", "repro_test.py"], cwd=self.workspace, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                print(f"   🎉 SUCCESS! Tests Passed on attempt {i+1}.")
                # 4. CRITIC: Final Review
                critique = self.ai.generate("Auditor", "Check for security/style.", f"Code: {solution}")
                self.write_file("review.md", critique)
                self.memory.save_experience(task, True, solution)
                return True
            else:
                print(f"   ❌ Test Failed. Retrying...")
                error_log = res.stderr + res.stdout

        print("   💀 Max retries reached.")
        self.memory.save_experience(task, False, solution)
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
