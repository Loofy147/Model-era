
import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the class to be tested
from autonomous_agent import SelfHealingAgent, MAX_RETRIES

class TestSelfHealingAgent(unittest.TestCase):

    def setUp(self):
        """Set up a clean workspace for each test."""
        self.workspace_dir = Path("_agent_workspace")
        self.workspace_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up the workspace after each test."""
        shutil.rmtree(self.workspace_dir, ignore_errors=True)

    @patch('autonomous_agent.AIClient')
    @patch('autonomous_agent.SelfHealingAgent.run_tests')
    def test_reflexion_loop_success_on_second_try(self, mock_run_tests, MockAIClient):
        """
        Verify the agent tries to fix code upon failure and stops upon success.
        """
        # --- MOCK SETUP ---
        # 1. Mock the AI to provide a sequence of responses
        mock_ai_instance = MockAIClient.return_value
        mock_ai_instance.generate.side_effect = [
            "PLAN_YAML",        # Initial plan
            "INITIAL_CODE",     # First attempt (will fail)
            "TEST_CODE",        # The test script
            "FIXED_CODE"        # Second attempt (will succeed)
        ]

        # 2. Mock the test runner to fail once, then succeed
        mock_run_tests.side_effect = [
            {"success": False, "stderr": "AssertionError: 1 != 2"}, # First run fails
            {"success": True, "stdout": "OK"}                       # Second run succeeds
        ]

        # --- EXECUTION ---
        agent = SelfHealingAgent()
        agent.execute_task("A test task that requires one fix")

        # --- ASSERTIONS ---
        # Check that the AI was called 4 times (plan, code, test, fix)
        self.assertEqual(mock_ai_instance.generate.call_count, 4)

        # Check that the test runner was called twice
        self.assertEqual(mock_run_tests.call_count, 2)

        # Check that the final code in the workspace is the "FIXED_CODE"
        final_code_path = self.workspace_dir / "solution.py"
        self.assertTrue(final_code_path.exists())
        with open(final_code_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "FIXED_CODE")

    @patch('autonomous_agent.AIClient')
    @patch('autonomous_agent.SelfHealingAgent.run_tests')
    def test_max_retries_reached(self, mock_run_tests, MockAIClient):
        """
        Verify the agent stops after hitting the MAX_RETRIES limit.
        """
        # --- MOCK SETUP ---
        # 1. Mock AI to keep generating "new" code
        mock_ai_instance = MockAIClient.return_value
        mock_ai_instance.generate.side_effect = [
            "PLAN_YAML", "CODE_V1", "TEST_CODE", "CODE_V2", "CODE_V3", "CODE_V4"
        ]

        # 2. Mock test runner to always fail
        mock_run_tests.return_value = {"success": False, "stderr": "SyntaxError"}

        # --- EXECUTION ---
        agent = SelfHealingAgent()
        # In the agent, MAX_RETRIES is 3, so we expect 3 test runs.
        agent.execute_task("A task that always fails")

        # --- ASSERTIONS ---
        # Check that the test runner was called exactly 3 times
        self.assertEqual(mock_run_tests.call_count, MAX_RETRIES)

if __name__ == '__main__':
    unittest.main()
