
import unittest
import os
import json
import argparse
import shutil
from unittest.mock import patch, MagicMock

# Import the classes to be tested
from flow_engineer import FlowEngineer
from main import main

class TestFlowIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a dummy repo map and workspace for testing."""
        self.map_file = "test_repo_map.json"
        self.workspace_dir = "_flow_workspace"

        # Clean up workspace before test
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)

        dummy_map = {
            "src/api.py": {
                "size": 120,
                "extension": ".py",
                "analysis": {
                    "definitions": [
                        {"type": "class", "name": "API", "doc": "Handles API requests."}
                    ]
                }
            }
        }
        with open(self.map_file, 'w') as f:
            json.dump(dummy_map, f)

    def tearDown(self):
        """Clean up dummy files and workspace."""
        if os.path.exists(self.map_file):
            os.remove(self.map_file)
        if os.path.exists('repo_map.json'):
             os.remove('repo_map.json')
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)

    def test_flow_engineer_initialization(self):
        """Test that the FlowEngineer class initializes correctly."""
        try:
            engineer = FlowEngineer(self.map_file)
            self.assertIsNotNone(engineer.repo_map)
            self.assertTrue(os.path.exists(self.workspace_dir))
        except Exception as e:
            self.fail(f"FlowEngineer initialization failed with {e}")

    @patch('flow_engineer.FlowEngineer.run_tests')
    @patch('flow_engineer.FlowEngineer.call_llm')
    def test_react_flow_handles_retry_and_succeeds(self, mock_call_llm, mock_run_tests):
        """Test the full ReAct loop with one failure and subsequent success."""
        # --- Mock AI Responses ---
        mock_plan = "plan:\\n  - file: 'solution.py'\\n    action: 'create'"
        mock_test_code = "import unittest\\nfrom solution import solve\\n\\nclass TestSolve(unittest.TestCase):\\n    def test_solve(self):\\n        self.assertEqual(solve(), 42)"
        failing_solution = "def solve():\\n    return 0"
        passing_solution = "def solve():\\n    return 42"

        mock_call_llm.side_effect = [
            mock_plan,
            mock_test_code,
            failing_solution,
            passing_solution
        ]

        # --- Mock Test Execution ---
        mock_run_tests.side_effect = [
            {"success": False, "stderr": "AssertionError: 0 != 42"},
            {"success": True, "stdout": "OK"}
        ]

        # --- Execute ---
        engineer = FlowEngineer(self.map_file)
        engineer.execute_flow("Implement the solve function")

        # --- Assert ---
        self.assertEqual(mock_call_llm.call_count, 4, "LLM should be called for plan, test, initial solve, and retry solve")
        self.assertEqual(mock_run_tests.call_count, 2, "Tests should be run twice (initial fail, retry success)")

        final_solution_path = os.path.join(self.workspace_dir, "solution.py")
        self.assertTrue(os.path.exists(final_solution_path))
        with open(final_solution_path, 'r') as f:
            content = f.read()

        cleaned_passing_solution = engineer._clean(passing_solution)
        self.assertEqual(content, cleaned_passing_solution)

    @patch('main.RepoCartographer')
    @patch('main.FlowEngineer')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_cli_integration(self, mock_parse_args, MockFlowEngineer, MockRepoCartographer):
        """Test that the main CLI script correctly invokes the components."""

        mock_cartographer_instance = MockRepoCartographer.return_value
        mock_engineer_instance = MockFlowEngineer.return_value

        task = "A test task for the CLI"
        mock_parse_args.return_value = argparse.Namespace(
            task=task,
            repo_path=".",
            map_file=self.map_file
        )

        try:
            main()
        except Exception as e:
            self.fail(f"Main CLI script failed when called directly: {e}")

        MockRepoCartographer.assert_called_with('.')
        mock_cartographer_instance.map_repo.assert_called_once()
        mock_cartographer_instance.export_map.assert_called_with(self.map_file)

        MockFlowEngineer.assert_called_with(self.map_file)
        mock_engineer_instance.execute_flow.assert_called_with(task)

if __name__ == '__main__':
    unittest.main()
