
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
    def test_team_manager_full_workflow(self, mock_subprocess_run, MockAIClient):
        # --- Mock AI Responses ---
        ai_instance = MockAIClient.return_value
        ai_instance.generate.side_effect = [
            # Planning Phase
            "plan: ...",  # Architect
            "APPROVED",    # Validator
            # Coding Phase
            "import unittest; ...",  # QA Engineer
            "def new_feature(): return 42",  # Coder
            # Auditor Phase
            "LGTM"  # Auditor
        ]

        # --- Mock Test Execution ---
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

        # --- Execute ---
        manager = TeamManager(self.task, self.target_file)

        # Manually step through the workflow to test orchestration logic
        # This gives us more granular control than calling execute_workflow() directly

        # 1. Plan
        manager._planning_phase()
        self.assertEqual(manager.context.current_state, "GENERATE_TESTS")
        self.assertIsNotNone(manager.context.plan)

        # 2. Generate Tests
        manager._test_generation_phase()
        self.assertEqual(manager.context.current_state, "CODING")
        self.assertIsNotNone(manager.context.test_code)

        # 3. Coding & Reflexion
        manager._coding_phase()
        self.assertEqual(manager.context.current_state, "AUDIT")
        self.assertIsNotNone(manager.context.solution_code)

        # 4. Audit
        manager._audit_phase()
        self.assertEqual(manager.context.current_state, "DONE")

        # Final check
        self.assertTrue(manager.execute_workflow())
        self.assertEqual(ai_instance.generate.call_count, 5)

if __name__ == '__main__':
    unittest.main()
