
import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock

# Since the classes are in the same file, we need to import them carefully
from main_hybrid import FlowEngineer, GitGatekeeper, RepoCartographer, MemoryManager

class TestHybridAgent(unittest.TestCase):

    def setUp(self):
        """Set up a clean workspace and dummy files for each test."""
        self.workspace_dir = "_agent_workspace"
        self.map_file = "repo_map.json"
        self.memory_file = "agent_memory.json"
        self.target_file = "src/test_file.py"

        # Clean up workspace and memory from previous runs
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)

        # Create dummy directories and files
        os.makedirs(os.path.dirname(self.target_file), exist_ok=True)
        with open(self.target_file, "w") as f:
            f.write("def old_function():\\n    return 0")

        dummy_map = {self.target_file: ["Function: old_function"]}
        with open(self.map_file, 'w') as f:
            json.dump(dummy_map, f)

    def tearDown(self):
        """Clean up all created files and directories."""
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        if os.path.exists(self.map_file):
            os.remove(self.map_file)
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
        if os.path.exists(os.path.dirname(self.target_file)):
            shutil.rmtree(os.path.dirname(self.target_file))

    @patch('main_hybrid.GitGatekeeper')
    @patch('main_hybrid.HybridAIClient')
    def test_memory_creation_and_retrieval(self, MockAIClient, MockGitGatekeeper):
        """
        Tests the full agentic loop with a focus on memory.
        - Run 1: Fails, but saves a memory of the failure.
        - Run 2: Succeeds, using the memory of the past failure to inform its decision.
        """
        ai_instance = MockAIClient.return_value
        task = "create a function that returns 42"

        # --- Mock AI Responses for BOTH runs ---
        approved_plan = "plan: detailed and correct plan"
        mock_test = "import unittest\\nfrom solution import new_function\\n\\nclass Test(unittest.TestCase):\\n    def test_logic(self): self.assertEqual(42, new_function())"
        failing_code = "def new_function(): return 99"
        passing_code = "def new_function(): return 42"

        ai_instance.generate.side_effect = [
            # Run 1
            approved_plan, "APPROVED",
            mock_test,
            failing_code, failing_code, failing_code,
            # Run 2
            approved_plan, "APPROVED",
            mock_test,
            passing_code,
            "LGTM",
        ]

        # --- Run 1 (Failure) ---
        mock_failed_process = MagicMock(returncode=1, stderr="Error", stdout="")
        with patch('subprocess.run', return_value=mock_failed_process):
            engineer = FlowEngineer()
            success1 = engineer.execute(task, self.target_file)

        self.assertFalse(success1)
        self.assertTrue(os.path.exists(self.memory_file))

        # --- Run 2 (Success) ---
        mock_success_process = MagicMock(returncode=0, stderr="", stdout="OK")
        with patch('subprocess.run', return_value=mock_success_process):
            engineer = FlowEngineer() # Re-instantiate to reload memories
            success2 = engineer.execute(task, self.target_file)

        self.assertTrue(success2)

        # --- Assertions ---
        # The first call to the Architect in the second run (call #6 overall)
        # should contain the memory of the first run's failure.
        architect_prompt_run2 = ai_instance.generate.call_args_list[6].args[2]
        self.assertIn("Similar Past Experiences", architect_prompt_run2)
        self.assertIn("Success: False", architect_prompt_run2)
        self.assertIn(failing_code, architect_prompt_run2)

if __name__ == '__main__':
    unittest.main()
