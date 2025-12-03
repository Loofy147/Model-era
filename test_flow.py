
import unittest
import os
import json
import argparse
from unittest.mock import patch, MagicMock

# Import the classes to be tested
from flow_engineer import FlowEngineer
from main import main

class TestFlowIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a dummy repo map for testing."""
        self.map_file = "test_repo_map.json"
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
        """Clean up the dummy repo map."""
        if os.path.exists(self.map_file):
            os.remove(self.map_file)
        if os.path.exists('repo_map.json'):
             os.remove('repo_map.json')

    def test_flow_engineer_initialization(self):
        """Test that the FlowEngineer class initializes correctly."""
        try:
            engineer = FlowEngineer(self.map_file)
            self.assertIsNotNone(engineer.repo_map)
        except Exception as e:
            self.fail(f"FlowEngineer initialization failed with {e}")

    @patch('flow_engineer.FlowEngineer.call_llm')
    def test_flow_execution_steps(self, mock_call_llm):
        """Test that the execute_flow method calls all three steps in order."""
        mock_call_llm.return_value = "MOCKED_YAML_PLAN"

        engineer = FlowEngineer(self.map_file)
        engineer.execute_flow("Test task")

        self.assertEqual(mock_call_llm.call_count, 3)

        first_call_args = mock_call_llm.call_args_list[0].args
        self.assertIn("You are a Senior Software Architect", first_call_args[0])

        second_call_args = mock_call_llm.call_args_list[1].args
        self.assertIn("You are a QA Engineer", second_call_args[0])

        third_call_args = mock_call_llm.call_args_list[2].args
        self.assertIn("You are a Senior Developer", third_call_args[0])

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
