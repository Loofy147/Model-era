
import json
import subprocess
from typing import Dict, List, Optional
from ai_client import AIClient
from pathlib import Path

# --- CONFIGURATION ---
REPO_MAP_PATH = "repo_map.json"
MAX_RETRIES = 3
WORKSPACE_DIR = "_flow_workspace"

class FlowEngineer:
    def __init__(self, repo_map_path: str):
        with open(repo_map_path, 'r') as f:
            self.repo_map = json.load(f)
        self.context_memory = []
        self.ai = AIClient()
        self.workspace = Path(WORKSPACE_DIR)
        self.workspace.mkdir(exist_ok=True)

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Connects to the AI model to generate a response.
        """
        print(f"\n🧠 [AI THINKING] System: {system_prompt[:50]}... | User: {user_prompt[:50]}...")
        return self.ai.generate(system_prompt, user_prompt)

    def step_1_planner(self, user_req: str) -> str:
        """
        Logic: Don't code. Just identify WHERE to code.
        """
        system_prompt = """
        You are a Senior Software Architect. You have a 'Repo Map' (JSON) of the codebase.
        Your goal is NOT to write code, but to create a 'Change Plan'.

        Rules:
        1. Identify which files need to be modified.
        2. Identify if new files need to be created.
        3. Output a strictly formatted YAML plan.
        """

        user_prompt = f"""
        Repo Context: {json.dumps(self.repo_map)[:10000]} # Truncate if too large
        User Request: {user_req}

        Output YAML format:
        plan:
          - file: "path/to/file.py"
            action: "modify" | "create"
            description: "What logic changes here."
        """

        print("--- 1. ARCHITECTING PLAN ---")
        plan = self.call_llm(system_prompt, user_prompt)
        self.context_memory.append(f"Plan: {plan}")
        return plan

    def step_2_test_generator(self, plan: str) -> str:
        """
        Logic: The 'Test-First' Principle.
        Before solving, create a script that reproduces the issue or verifies the feature.
        """
        system_prompt = """
        You are a QA Engineer. Given a 'Change Plan', write a standalone Python script
        named 'reproduction_script.py'.

        Rules:
        1. The script must fail if the feature is not implemented.
        2. The script must pass if the feature works.
        3. Do not mock internal logic if possible; import the actual classes.
        """

        user_prompt = f"Plan: {plan}\n\nWrite the 'reproduction_script.py'."

        print("--- 2. GENERATING TEST HARNESS ---")
        test_code = self.call_llm(system_prompt, user_prompt)
        return test_code

    def step_3_solver(self, plan: str, test_code: str) -> str:
        """
        Logic: The 'Solver'. Writes the actual code.
        """
        system_prompt = """
        You are a Senior Developer. Implement the changes defined in the Plan.
        You must ensure the code passes the 'reproduction_script.py' provided.
        """

        user_prompt = f"""
        Plan: {plan}
        Test Script: {test_code}

        Please provide the full code for the modified files.
        """

        print("--- 3. WRITING CODE ---")
        solution = self.call_llm(system_prompt, user_prompt)
        return solution

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
                timeout=15
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

    def _clean(self, text):
        return text.replace("```python", "").replace("```", "").strip()

    def execute_flow(self, user_request: str):
        print(f"🚀 STARTING FLOW: '{user_request}'")

        plan = self.step_1_planner(user_request)
        print(f"📋 Initial Plan Generated:\n{plan}\n")

        test_code = self.step_2_test_generator(plan)
        self.write_to_workspace("test_suite.py", self._clean(test_code))

        solution_code = self.step_3_solver(plan, test_code)
        self.write_to_workspace("solution.py", self._clean(solution_code))

        attempt = 0
        while attempt < MAX_RETRIES:
            print(f"\n🔄 Attempt {attempt + 1}/{MAX_RETRIES}: Running Verification...")

            result = self.run_tests("test_suite.py")

            if result["success"]:
                print("   ✅ SUCCESS! Tests Passed.")
                print(f"   🎉 Final verified code is in {self.workspace}/solution.py")
                return

            print("   ❌ FAILED. Analyzing traceback...")
            error_msg = result["stderr"] if result["stderr"] else result["stdout"]
            print(f"   📝 Error Snippet: {error_msg[:200]}...")

            with open(self.workspace / 'solution.py', 'r') as f:
                current_code = f.read()

            reflection_prompt_user = f"The previous code attempt failed.\nOriginal Task: {user_request}\nOriginal Plan: {plan}\nTest Script that Failed:\n{test_code}\n\nCurrent (Failing) Code:\n{current_code}\n\nError Message:\n{error_msg}\n\nPlease analyze the error and the code, then rewrite the FULL 'solution.py' to fix the error."
            reflection_prompt_system = "You are a Senior Debugger. Your task is to fix failing code based on test results. Provide only the complete, corrected Python code for the file."

            new_code = self.call_llm(reflection_prompt_system, reflection_prompt_user)
            self.write_to_workspace("solution.py", self._clean(new_code))
            attempt += 1

        print("\n💀 MAX RETRIES REACHED. The agent could not solve the problem.")

# --- EXECUTION ---
if __name__ == "__main__":
    # Point this to your repo_map.json generated in Phase 1
    if not Path(REPO_MAP_PATH).exists():
        print(f"Error: Repository map file '{REPO_MAP_PATH}' not found. Please run the repo cartographer first.")
        exit(1)

    engine = FlowEngineer(REPO_MAP_PATH)

    # Example Task
    task = "Add a rate_limiter to the API class that allows 5 requests per minute."
    engine.execute_flow(task)
