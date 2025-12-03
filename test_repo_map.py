
import unittest
import os
import shutil
import json
from repo_map import map_repo, get_ignore_patterns

class TestRepoMap(unittest.TestCase):

    def setUp(self):
        """Set up a temporary test directory structure."""
        self.test_dir = 'test_repo'
        os.makedirs(self.test_dir, exist_ok=True)

        # Create dummy files and directories
        os.makedirs(os.path.join(self.test_dir, 'src'))
        with open(os.path.join(self.test_dir, 'src', 'main.py'), 'w') as f:
            f.write('print("hello")')

        os.makedirs(os.path.join(self.test_dir, '.git'))
        with open(os.path.join(self.test_dir, '.git', 'config'), 'w') as f:
            f.write('[core]')

        os.makedirs(os.path.join(self.test_dir, 'data'))
        with open(os.path.join(self.test_dir, 'data', 'data.csv'), 'w') as f:
            f.write('a,b,c')

        with open(os.path.join(self.test_dir, 'README.md'), 'w') as f:
            f.write('# Test Repo')

        # Create a .gptignore file
        with open(os.path.join(self.test_dir, '.gptignore'), 'w') as f:
            f.write('data/\n*.csv\n')

    def tearDown(self):
        """Remove the temporary test directory."""
        shutil.rmtree(self.test_dir)

    def test_basic_mapping(self):
        """Test the basic mapping of the repository."""
        ignore_patterns = get_ignore_patterns(os.path.join(self.test_dir, '.gptignore'))
        repo_map = map_repo(self.test_dir, ignore_patterns)

        # Check root properties
        self.assertEqual(repo_map['name'], 'test_repo')
        self.assertEqual(repo_map['type'], 'directory')

        # Get children names for easier checking
        children_names = [child['name'] for child in repo_map['children']]

        # Check that ignored files are not present and others are
        self.assertNotIn('.git', children_names)
        self.assertNotIn('data', children_names)
        self.assertIn('src', children_names)
        self.assertIn('README.md', children_names)

        # Check nested structure
        src_dir = next(child for child in repo_map['children'] if child['name'] == 'src')
        self.assertEqual(len(src_dir['children']), 1)
        self.assertEqual(src_dir['children'][0]['name'], 'main.py')

    def test_no_ignore_file(self):
        """Test mapping with default ignore patterns when no ignore file is present."""
        # Remove the gptignore file for this test
        os.remove(os.path.join(self.test_dir, '.gptignore'))

        ignore_patterns = get_ignore_patterns(os.path.join(self.test_dir, '.gptignore'))
        repo_map = map_repo(self.test_dir, ignore_patterns)

        children_names = [child['name'] for child in repo_map['children']]

        # Default .git should be ignored
        self.assertNotIn('.git', children_names)
        # Without the ignore file, 'data' should now be present
        self.assertIn('data', children_names)

if __name__ == '__main__':
    unittest.main()
