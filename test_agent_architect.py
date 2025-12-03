
import unittest
import os
import shutil
import json
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the classes from the script to be tested
from agent_architect import RepoCartographer, FlowEngineer

class TestAgentArchitect(unittest.TestCase):

    def setUp(self):
        """Set up a test environment."""
        self.test_dir = Path("test_repo_for_agent")
        self.test_dir.mkdir(exist_ok=True)
        self.workspace_dir = "_agent_workspace"
        self.repo_map_file = "repo_map.json"

        # Create a dummy file for the cartographer to find
        with open(self.test_dir / "app.py", "w") as f:
            f.write("def hello():\n    return 'world'")

    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.workspace_dir, ignore_errors=True)
        if os.path.exists(self.repo_map_file):
            os.remove(self.repo_map_file)

    def test_repo_cartographer(self):
        """Test the mapping functionality."""
        cartographer = RepoCartographer(str(self.test_dir))
        cartographer.map_repo()

        # Check that the file was found and processed
        self.assertTrue(os.path.exists(self.repo_map_file))
        with open(self.repo_map_file, 'r') as f:
            repo_map = json.load(f)

        self.assertIn("app.py", repo_map)
        self.assertIn("Function: hello()", repo_map["app.py"]["summary"])

    @patch('agent_architect.AIClient')
    def test_flow_engineer_workflow(self, MockAIClient):
        """Test the full workflow orchestration with a mocked AI."""
        # Setup the mock AI to return predictable responses
        mock_ai_instance = MockAIClient.return_value
        mock_ai_instance.generate.side_effect = [
            "PLAN_YAML",
            "TEST_CODE",
            "SOLUTION_CODE",
            "CRITIQUE_TEXT"
        ]

        # Create a dummy repo map for the flow engineer
        with open(self.repo_map_file, "w") as f:
            json.dump({"dummy_file.py": {"summary": "dummy"}}, f)

        engine = FlowEngineer()
        engine.execute_task("A test task")

        # Verify that all steps were called and artifacts were created
        self.assertEqual(mock_ai_instance.generate.call_count, 4)

        self.assertTrue(os.path.exists(os.path.join(self.workspace_dir, "1_plan.yaml")))
        self.assertTrue(os.path.exists(os.path.join(self.workspace_dir, "2_test_harness.py")))
        self.assertTrue(os.path.exists(os.path.join(self.workspace_dir, "3_solution.py")))
        self.assertTrue(os.path.exists(os.path.join(self.workspace_dir, "4_critique.txt")))

if __name__ == '__main__':
    unittest.main()
