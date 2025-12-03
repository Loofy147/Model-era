
import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock

# Since the classes are in the same file, we need to import them carefully
from main_hybrid import FlowEngineer, GitGatekeeper, RepoCartographer

class TestHybridAgent(unittest.TestCase):

    def setUp(self):
        """Set up a clean workspace and dummy files for each test."""
        self.workspace_dir = "_agent_workspace"
        self.map_file = "repo_map.json"
        self.target_file = "src/test_file.py"

        # Create dummy directories and files for a realistic test
        os.makedirs(os.path.dirname(self.target_file), exist_ok=True)
        with open(self.target_file, "w") as f:
            f.write("def old_function():\\n    return 0")

        # Clean up workspace from previous runs
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)

        # Create a dummy repo map
        dummy_map = {self.target_file: ["Function: old_function"]}
        with open(self.map_file, 'w') as f:
            json.dump(dummy_map, f)

    def tearDown(self):
        """Clean up all created files and directories."""
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        if os.path.exists(self.map_file):
            os.remove(self.map_file)
        if os.path.exists(os.path.dirname(self.target_file)):
            shutil.rmtree(os.path.dirname(self.target_file))

    @patch('main_hybrid.GitGatekeeper')
    @patch('main_hybrid.HybridAIClient')
    def test_planning_and_reflexion_loop(self, MockAIClient, MockGitGatekeeper):
        """
        Tests the entire agentic loop, including a plan rejection and a code retry.
        - Mocks the AI to simulate a flawed plan, a correction, a code failure, and a success.
        - Verifies that the agent correctly cycles through both planning and coding loops.
        """
        # --- Mock AI Responses ---
        ai_instance = MockAIClient.return_value

        # Phase 1: Planning
        flawed_plan = "plan: vague plan"
        validator_critique = "Critique: The plan is too vague. Please provide details."
        approved_plan = "plan: detailed and correct plan"

        # Phase 2: Coding
        mock_test = "import unittest\\nfrom solution import new_function\\n\\nclass MyTest(unittest.TestCase):\\n    def test_logic(self):\\n        self.assertEqual(42, new_function())"
        failing_code = "def new_function():\\n    return 99"
        passing_code = "def new_function():\\n    return 42"
        mock_critique = "LGTM"

        ai_instance.generate.side_effect = [
            # Planning Loop
            flawed_plan,         # Architect (Attempt 1)
            validator_critique,  # Validator -> Rejects
            approved_plan,       # Architect (Attempt 2)
            "APPROVED",          # Validator -> Approves
            # Coding Loop
            mock_test,           # QA Engineer
            failing_code,        # Python Dev (Attempt 1)
            passing_code,        # Python Dev (Attempt 2)
            mock_critique        # Auditor
        ]

        # --- Mock subprocess for test execution ---
        mock_failed_process = MagicMock(returncode=1, stderr="AssertionError: 99 != 42", stdout="")
        mock_success_process = MagicMock(returncode=0, stderr="", stdout="OK")

        with patch('subprocess.run', side_effect=[mock_failed_process, mock_success_process]) as mock_run:
            # --- Execute ---
            engineer = FlowEngineer()
            success = engineer.execute("a test task", self.target_file)

            # --- Assertions ---
            self.assertTrue(success)
            # Architect (2), Validator (2), QA (1), Dev (2), Auditor (1) = 8 calls
            self.assertEqual(ai_instance.generate.call_count, 8)
            self.assertEqual(mock_run.call_count, 2)

            # Check that the final approved plan was written
            with open(os.path.join(self.workspace_dir, "plan.yaml"), 'r') as f:
                self.assertEqual(f.read().strip(), approved_plan)

            # Check that the final solution was correctly written
            with open(os.path.join(self.workspace_dir, "solution.py"), 'r') as f:
                self.assertEqual(f.read().strip(), passing_code)

if __name__ == '__main__':
    unittest.main()
