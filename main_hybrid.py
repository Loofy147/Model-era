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
from logger import get_logger

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

class AgentError(Exception):
    """Custom exception for agent-related errors."""
    def __init__(self, agent: str, phase: str, details: dict):
        self.agent = agent
        self.phase = phase
        self.details = details
        super().__init__(f"AgentError: {agent} failed in {phase} with details: {json.dumps(details)}")

# Initialize a global logger
logger = get_logger(__name__)

class Metrics:
    """A simple class to collect and store metrics."""
    def __init__(self):
        self.data = []

    def record(self, metric: dict):
        self.data.append(metric)

    def get_all(self):
        return self.data

# MODEL ROSTER (Adjust based on your availability)
# Tier 1: High Intelligence, High Cost
MODEL_ARCHITECT = "gpt-4o"
from contextlib import contextmanager
import time

@contextmanager
def track_agent_execution(agent_name: str, phase: str, metrics: Metrics):
    """
    A context manager to track the execution time and token usage of an agent.
    """
    start_time = time.time()
    # In a real implementation, you would get the token usage from the AI client
    tokens_used = 0
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record({
            "agent": agent_name,
            "phase": phase,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used
        })
# Tier 2: High Skill, Zero/Low Cost (Local or Cheap API)
# Use "ollama/qwen2.5-coder:14b" if running locally, or "gpt-4o-mini" / "groq/..."
MODEL_CODER = "ollama/qwen2.5-coder:14b"
# Tier 3: Fast, Zero Cost
MODEL_CLERK = "ollama/llama3.2"

# Fallback: If local models fail, use this cheap cloud model
MODEL_FALLBACK = "gpt-4o-mini"

class SecurityError(Exception):
    """Custom exception for security violations."""
    pass

class InputValidator:
    """
    Validates and sanitizes user input to prevent security risks like prompt injection.
    """
    MAX_INSTRUCTION_LENGTH = 2000
    PROMPT_INJECTION_PATTERNS = [
        "ignore previous", "ignore all", "system:", "disregard",
        "act as", "you are a", "roleplay as"
    ]

    @staticmethod
    def validate_instruction(text: str) -> str:
        """
        Validates the user's instruction.

        Raises:
            ValueError: If the instruction is too long.
            SecurityError: If a potential prompt injection is detected.

        Returns:
            The original text if it's valid.
        """
        if len(text) > InputValidator.MAX_INSTRUCTION_LENGTH:
            raise ValueError(f"Instruction exceeds maximum length of {InputValidator.MAX_INSTRUCTION_LENGTH} characters.")

        lower_text = text.lower()
        for pattern in InputValidator.PROMPT_INJECTION_PATTERNS:
            if pattern in lower_text:
                raise SecurityError(f"Potential prompt injection detected: found '{pattern}'.")

        return text

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

        logger.info(f"Routing '{role}' to {model}", details={"role": role, "model": model, "temperature": temp})

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
            logger.error(f"Error with {model}: {e}", extra={'details': {"model": model, "error": str(e)}})
            if model != MODEL_FALLBACK:
                logger.info(f"Retrying with Fallback ({MODEL_FALLBACK})...")
                try:
                    response = completion(
                        model=MODEL_FALLBACK,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
                    )
                    return response.choices[0].message.content
                except Exception as e2:
                    logger.error(f"Fallback model failed: {e2}", extra={'details': {"model": MODEL_FALLBACK, "error": str(e2)}})
                    raise AgentError(role, "generation", {"original_error": str(e), "fallback_error": str(e2)})
            raise AgentError(role, "generation", {"error": str(e)})

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
        logger.info(f"🌿 Created branch: {branch}")
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
        logger.info("Experience saved to memory.", extra={'details': {"task": task, "success": success}})

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

# --- 5. MULTI-AGENT COLLABORATION FRAMEWORK ---
class SharedContext:
    """A structured scratchpad for agents to read from and write to."""
    def __init__(self, task, target_file, repo_map, similar_experiences):
        self.task = task
        self.target_file = target_file
        self.repo_map = repo_map
        self.similar_experiences = similar_experiences
        self.plan = ""
        self.test_code = ""
        self.solution_code = ""
        self.critique = ""
        self.error_log = ""
        self.current_state = "PLANNING" # Initial state

    def __str__(self):
        return f"**Context**:\n- Task: {self.task}\n- State: {self.current_state}\n- Plan: {'Yes' if self.plan else 'No'}\n- Test: {'Yes' if self.test_code else 'No'}"

# Agent Personas and System Prompts
AGENT_PERSONAS = {
    "ARCHITECT": {
        "role": "Architect",
        "system_prompt": """
You are a Senior Software Architect. Create a detailed, multi-step YAML execution plan.
Incorporate lessons from past experiences. A good plan is critical.
Output a strict YAML with `thought_process`, `edge_cases`, and `plan` sections.
"""
    },
    "VALIDATOR": {
        "role": "Validator",
        "system_prompt": """
You are a Plan Validator. Review a YAML plan.
If it is logical, feasible, and detailed, respond with "APPROVED".
Otherwise, provide a brief, constructive critique.
"""
    },
    "QA_ENGINEER": {
        "role": "QA Engineer",
        "system_prompt": "You are a Test Engineer. Write a Python script 'repro_test.py' based on the plan. It must fail if the feature is not implemented and pass if it is."
    },
    "CODER": {
        "role": "Python Dev",
        "system_prompt": "You are a Senior Python Developer. Write the full code for the target file to pass the test harness. You must respond with only the code."
    },
    "DEBUGGER": {
        "role": "Debugger",
        "system_prompt": "You are a Debugger. Your previous code failed. Analyze the error and the test harness, then rewrite the full code to fix the issue. Respond with only the code."
    },
    "AUDITOR": {
        "role": "Auditor",
        "system_prompt": "You are a Security and Style Auditor. Review the final code for security vulnerabilities, style issues, and adherence to the plan. Provide a brief review."
    },
    "REFACTOR_AGENT": {
        "role": "Python Dev",
        "system_prompt": "You are a Refactoring Agent. Your task is to rewrite the given Python code to fix all issues reported by the flake8 linter. Respond with only the full, corrected code."
    }
}

class Agent:
    """A generic agent that can perform a single turn."""
    def __init__(self, persona: Dict[str, str], ai_client: HybridAIClient, metrics: Metrics):
        self.persona = persona
        self.ai = ai_client
        self.metrics = metrics

    def execute_turn(self, context: SharedContext, user_prompt: str) -> str:
        """Generates a response based on the agent's persona and the shared context."""
        with track_agent_execution(self.persona['role'], context.current_state, self.metrics):
            return self.ai.generate(
                role=self.persona["role"],
                system_prompt=self.persona["system_prompt"],
                user_prompt=user_prompt
            )

class TeamManager:
    def __init__(self, task, target_file):
        self.ai = HybridAIClient()
        self.memory = MemoryManager()
        self.workspace = Path(WORKSPACE_DIR)
        self.metrics = Metrics()

        repo_map = self._load_map()
        similar_experiences = self.memory.find_similar_experiences(task)
        self.context = SharedContext(task, target_file, repo_map, similar_experiences)

        self.agents = {name: Agent(persona, self.ai, self.metrics) for name, persona in AGENT_PERSONAS.items()}

    def _load_map(self):
        repo_map_path = Path(REPO_MAP_FILE)
        if not repo_map_path.exists():
            return RepoCartographer().map_repo()
        with open(repo_map_path) as f:
            return json.load(f)

    def execute_workflow(self):
        logger.info(f"Starting agent team for: {self.context.task}", extra={'details': {"task": self.context.task}})

        while self.context.current_state not in ["DONE", "FAILED"]:
            logger.info(f"Current state: {self.context.current_state}", extra={'details': {"state": self.context.current_state}})

            if self.context.current_state == "PLANNING":
                self._planning_phase()
            elif self.context.current_state == "GENERATE_TESTS":
                self._test_generation_phase()
            elif self.context.current_state == "CODING":
                self._coding_phase()
            elif self.context.current_state == "REFACTORING":
                self._refactoring_phase()
            elif self.context.current_state == "AUDIT":
                self._audit_phase()

        if self.context.current_state == "DONE":
            logger.info("Workflow complete.", extra={'details': {"task": self.context.task}})
            self.memory.save_experience(self.context.task, True, self.context.solution_code)
            return True
        else:
            logger.error("Workflow failed.", extra={'details': {"task": self.context.task}})
            self.memory.save_experience(self.context.task, False, self.context.solution_code)

            # Print metrics at the end of the workflow
            logger.info("Execution Metrics:", extra={'details': {"metrics": self.metrics.get_all()}})
            return False

    def _planning_phase(self):
        experiential_context = "\n".join([f"- Task: {exp['task']}\n  Success: {exp['success']}\n  Solution:\n```python\n{exp['solution']}\n```" for exp in self.context.similar_experiences])

        for i in range(MAX_RETRIES):
            plan_prompt = f"Similar Past Experiences:\n{experiential_context}\n\nCodebase Map:\n{str(self.context.repo_map)[:3000]}\n\nTarget: `{self.context.target_file}`\nRequest: \"{self.context.task}\"\nPrior Critique: {self.context.critique}\n\nGenerate or revise the YAML execution plan."
            plan = self.agents["ARCHITECT"].execute_turn(self.context, plan_prompt)

            validation_prompt = f"Please validate this plan:\n\n---\n{plan}\n---"
            validation = self.agents["VALIDATOR"].execute_turn(self.context, validation_prompt)

            if "APPROVED" in validation.upper():
                logger.info(f"Plan approved on attempt {i+1}.", extra={'details': {"attempt": i+1}})
                self.context.plan = plan
                self.context.current_state = "GENERATE_TESTS"
                return
            else:
                self.context.critique = validation
                logger.warning("Plan rejected.", extra={'details': {"critique": self.context.critique}})

        logger.error("Max retries reached for planning.", extra={'details': {"max_retries": MAX_RETRIES}})
        self.context.current_state = "FAILED"

    def _test_generation_phase(self):
        test_prompt = f"Plan: {self.context.plan}\nWrite a Python script 'repro_test.py' that reproduces the issue or validates the new feature. It MUST fail initially."
        self.context.test_code = self.agents["QA_ENGINEER"].execute_turn(self.context, test_prompt)
        self._write_to_workspace("repro_test.py", self.context.test_code)
        logger.info("Test harness created.")
        self.context.current_state = "CODING"

    def _coding_phase(self):
        experiential_context = "\n".join([f"- Task: {exp['task']}\n  Success: {exp['success']}\n  Solution:\n```python\n{exp['solution']}\n```" for exp in self.context.similar_experiences])

        for i in range(MAX_RETRIES):
            if i == 0:
                code_prompt = f"Plan:\n{self.context.plan}\n\nTest Harness:\n{self.context.test_code}\n\nWrite the full code for `{self.context.target_file}` to pass the test."
                agent = self.agents["CODER"]
            else:
                code_prompt = f"Your previous code failed the tests.\nError:\n{self.context.error_log}\n\nTest Harness:\n{self.context.test_code}\n\nRewrite the full code for `{self.context.target_file}` to fix the error."
                agent = self.agents["DEBUGGER"]

            solution = agent.execute_turn(self.context, code_prompt)
            self.context.solution_code = solution
            self._write_to_workspace("solution.py", solution)

            res = subprocess.run(["python", "repro_test.py"], cwd=self.workspace, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                logger.info(f"Tests passed on attempt {i+1}.", extra={'details': {"attempt": i+1}})
                self.context.current_state = "REFACTORING"
                return
            else:
                logger.warning("Test failed. Retrying...", extra={'details': {"attempt": i+1, "error": res.stderr + res.stdout}})
                self.context.error_log = res.stderr + res.stdout

        logger.error("Max retries reached for coding.", extra={'details': {"max_retries": MAX_RETRIES}})
        self.context.current_state = "FAILED"

    def _refactoring_phase(self):
        for i in range(MAX_RETRIES):
            lint_results = self._run_linter(self.workspace / "solution.py")
            if not lint_results:
                logger.info("Linter passed.")
                self.context.current_state = "AUDIT"
                return

            logger.warning("Linter found issues.", extra={'details': {"lint_results": lint_results}})

            refactor_prompt = f"The following code has linting errors:\n\n```python\n{self.context.solution_code}\n```\n\nLinter Output:\n{lint_results}\n\nPlease rewrite the full code to fix these issues."

            new_code = self.agents["REFACTOR_AGENT"].execute_turn(self.context, refactor_prompt)
            self.context.solution_code = new_code
            self._write_to_workspace("solution.py", new_code)

            # Re-run tests to ensure refactoring didn't break anything
            res = subprocess.run(["python", "repro_test.py"], cwd=self.workspace, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                logger.error("Refactoring broke the tests. Failing workflow.", extra={'details': {"error": res.stderr + res.stdout}})
                self.context.current_state = "FAILED"
                return

            logger.info("Refactoring successful and tests still pass.")

        logger.warning("Max retries reached for refactoring. Proceeding to audit.", extra={'details': {"max_retries": MAX_RETRIES}})
        self.context.current_state = "AUDIT" # Proceed to audit even if linting fails

    def _audit_phase(self):
        audit_prompt = f"Code:\n{self.context.solution_code}"
        self.context.critique = self.agents["AUDITOR"].execute_turn(self.context, audit_prompt)
        logger.info(f"Auditor's Review: {self.context.critique}", extra={'details': {"critique": self.context.critique}})
        self.context.current_state = "DONE"

    def _write_to_workspace(self, filename, content):
        clean_content = content.replace("```python", "").replace("```", "").strip()
        with open(self.workspace / filename, "w") as f:
            f.write(clean_content)

    def _run_linter(self, file_path):
        try:
            result = subprocess.run(
                ["flake8", str(file_path)],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            return "flake8 not found. Please install it with 'pip install flake8'."

# --- 6. MAIN ENTRY POINT ---
def main():
    parser = argparse.ArgumentParser(description="Hybrid Neuro-Symbolic Agent")
    parser.add_argument("file", help="Target file to modify")
    parser.add_argument("instruction", help="Natural language instruction")
    parser.add_argument("--remap", action="store_true", help="Force regenerate repo map")
    args = parser.parse_args()

    if args.remap and Path(REPO_MAP_FILE).exists():
        os.remove(REPO_MAP_FILE)

    # Initialize System
    git = GitGatekeeper()
    current_branch = git.run(["rev-parse", "--abbrev-ref", "HEAD"])

    try:
        # Validate user input before proceeding
        validated_instruction = InputValidator.validate_instruction(args.instruction)

        # Create Sandbox Branch
        branch = git.create_branch(validated_instruction)

        # Run Logic
        manager = TeamManager(validated_instruction, args.file)
        success = manager.execute_workflow()

        if success:
            # Move from Sandbox to Real Repo
            src = manager.workspace / "solution.py"
            dst = Path(args.file)
            shutil.copy(src, dst)
            logger.info(f"Transplanted solution to {dst}", details={"source": str(src), "destination": str(dst)})

            git.commit(validated_instruction)
            logger.info(f"Committed changes to branch {branch}", extra={'details': {"branch": branch}})
        else:
            logger.error("Task failed. Reverting branch.", extra={'details': {"branch": branch}})
            git.run(["checkout", current_branch])
            git.run(["branch", "-D", branch])

    except (ValueError, SecurityError) as e:
        logger.error(f"Input validation failed: {e}", extra={'details': {"error": str(e)}})
    except AgentError as e:
        logger.error(f"Agent failed: {e}", extra={'details': {"agent": e.agent, "phase": e.phase, "details": e.details}})
    except KeyboardInterrupt:
        logger.warning("Aborted by user.")
        git.run(["checkout", current_branch])

if __name__ == "__main__":
    main()
