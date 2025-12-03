
import unittest
import os
import shutil
import json
from pathlib import Path
from repo_map import RepoCartographer

class TestRepoCartographer(unittest.TestCase):

    def setUp(self):
        """Set up a temporary test directory structure for the cartographer."""
        self.test_dir = Path('test_project')
        self.test_dir.mkdir(exist_ok=True)

        # --- Create a structure with code and items to be ignored ---

        # 1. A Python file with classes and functions
        src_dir = self.test_dir / 'src'
        src_dir.mkdir()
        with open(src_dir / 'main.py', 'w') as f:
            f.write('"""Module docstring."""\n'
                    'class MyClass:\n'
                    '    """A simple class."""\n'
                    '    pass\n\n'
                    'def my_function(arg1, arg2):\n'
                    '    """A simple function."""\n'
                    '    return arg1 + arg2\n')

        # 2. An empty Python file
        with open(src_dir / 'empty.py', 'w') as f:
            pass

        # 3. A file with a syntax error
        with open(src_dir / 'bad_syntax.py', 'w') as f:
            f.write('def = 1')

        # 4. A non-Python source file
        with open(src_dir / 'script.js', 'w') as f:
            f.write('console.log("hello");')

        # 5. Ignored directories and files
        (self.test_dir / '.git').mkdir()
        (self.test_dir / 'node_modules').mkdir()
        with open(self.test_dir / '.DS_Store', 'w') as f:
            f.write('junk')

    def tearDown(self):
        """Remove the temporary test directory."""
        shutil.rmtree(self.test_dir)
        if os.path.exists('repo_map.json'):
            os.remove('repo_map.json')

    def test_is_ignored(self):
        """Test the logic for ignoring files and directories."""
        cartographer = RepoCartographer(self.test_dir)
        self.assertTrue(cartographer.is_ignored(self.test_dir / '.git' / 'config'))
        self.assertTrue(cartographer.is_ignored(self.test_dir / 'node_modules' / 'lib'))
        self.assertTrue(cartographer.is_ignored(self.test_dir / '.DS_Store'))
        self.assertFalse(cartographer.is_ignored(self.test_dir / 'src' / 'main.py'))

    def test_parse_python_ast(self):
        """Test the AST parsing for classes, functions, and docstrings."""
        cartographer = RepoCartographer(self.test_dir)
        content = (
            'class TestClass:\n'
            '    """Class doc."""\n'
            '    pass\n\n'
            'def test_func(a, b):\n'
            '    """Func doc."""\n'
            '    pass\n'
        )
        analysis = cartographer.parse_python_ast(content)

        self.assertIn('definitions', analysis)
        defs = analysis['definitions']
        self.assertEqual(len(defs), 2)

        # Order might vary, so check contents
        class_def = next((d for d in defs if d['type'] == 'class'), None)
        func_def = next((d for d in defs if d['type'] == 'function'), None)

        self.assertIsNotNone(class_def)
        self.assertEqual(class_def['name'], 'TestClass')
        self.assertEqual(class_def['doc'], 'Class doc.')

        self.assertIsNotNone(func_def)
        self.assertEqual(func_def['name'], 'test_func')
        self.assertEqual(func_def['args'], ['a', 'b'])
        self.assertTrue(func_def['doc'].startswith('Func doc.'))

    def test_map_repo_structure_and_analysis(self):
        """End-to-end test of mapping the repository."""
        cartographer = RepoCartographer(self.test_dir)
        cartographer.map_repo()

        structure = cartographer.project_structure

        # Check that ignored files are excluded
        self.assertNotIn('.DS_Store', structure)

        # Check that valid source files are included
        self.assertIn('src/main.py', structure)
        self.assertIn('src/empty.py', structure)
        self.assertIn('src/bad_syntax.py', structure)
        self.assertIn('src/script.js', structure)

        # Deep check the analysis of main.py
        main_py_analysis = structure['src/main.py']['analysis']
        self.assertIn('definitions', main_py_analysis)
        defs = main_py_analysis['definitions']
        self.assertEqual(len(defs), 2)
        self.assertEqual(defs[0]['name'], 'MyClass')
        self.assertEqual(defs[1]['name'], 'my_function')

        # Check syntax error handling
        bad_syntax_analysis = structure['src/bad_syntax.py']['analysis']
        self.assertEqual(bad_syntax_analysis.get('error'), 'Syntax Error in parsing')

    def test_export_map(self):
        """Test the JSON export functionality."""
        cartographer = RepoCartographer(self.test_dir)
        cartographer.map_repo()
        cartographer.export_map()

        self.assertTrue(os.path.exists('repo_map.json'))
        with open('repo_map.json', 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 4) # 4 processed files
        self.assertIn('src/main.py', data)

if __name__ == '__main__':
    unittest.main()
