
import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock

from main_hybrid import TeamManager, GitGatekeeper, AGENT_PERSONAS

class TestTeamManager(unittest.TestCase):

    def setUp(self):
        self.workspace_dir = "_agent_workspace"
        self.map_file = "repo_map.json"
        self.memory_file = "agent_memory.json"
        self.target_file = "src/test_file.py"
        self.task = "Implement a new feature"

        # Clean up and set up dummy files
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
        os.makedirs(os.path.dirname(self.target_file), exist_ok=True)
        with open(self.target_file, "w") as f:
            f.write("def old_function(): pass")
        with open(self.map_file, "w") as f:
            json.dump({self.target_file: ["old_function"]}, f)

    def tearDown(self):
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        if os.path.exists(self.map_file):
            os.remove(self.map_file)
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
        if os.path.exists(os.path.dirname(self.target_file)):
            shutil.rmtree(os.path.dirname(self.target_file))

    @patch('main_hybrid.HybridAIClient')
    @patch('main_hybrid.subprocess.run')
    def test_refactoring_phase(self, mock_subprocess_run, MockAIClient):
        # --- Mock AI Responses ---
        ai_instance = MockAIClient.return_value
        messy_code = "import os\\ndef new_feature():\\n    return 42"
        clean_code = "import os\\n\\n\\ndef new_feature():\\n    return 42"
        ai_instance.generate.side_effect = [
            # Planning & Coding
            "plan: ...", "APPROVED", "import unittest; ...", messy_code,
            # Refactoring
            clean_code,
            # Auditing
            "LGTM"
        ]

        # --- Mock Linter and Test Execution ---
        # 1. Initial test run (pass)
        # 2. Linter run (fail)
        # 3. Test re-run after refactor (pass)
        # 4. Final linter run (pass)
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0, stdout="OK"), # Test pass
            MagicMock(returncode=1, stdout="E501 line too long"), # Linter fail
            MagicMock(returncode=0, stdout="OK"), # Test re-run pass
            MagicMock(returncode=0, stdout=""), # Linter pass
        ]

        # --- Execute ---
        manager = TeamManager(self.task, self.target_file)
        success = manager.execute_workflow()

        # --- Assertions ---
        self.assertTrue(success)
        self.assertEqual(manager.context.current_state, "DONE")
        # Plan, Validate, QA, Coder, Refactor, Auditor
        self.assertEqual(ai_instance.generate.call_count, 6)
        # Test, Lint, Test, Lint
        self.assertEqual(mock_subprocess_run.call_count, 4)
        # Verify final code is the clean version
        self.assertEqual(manager.context.solution_code, clean_code)

if __name__ == '__main__':
    unittest.main()
