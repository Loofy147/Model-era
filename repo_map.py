
import os
import fnmatch
from typing import List, Dict, Any

def get_ignore_patterns(ignore_file_path: str) -> List[str]:
    """
    Reads patterns from a .gptignore file and returns them.
    Includes default patterns to ignore common directories.
    """
    default_patterns = ['.git/', 'node_modules/', '__pycache__/', '*.pyc', '*.log']
    if not os.path.exists(ignore_file_path):
        return default_patterns

    with open(ignore_file_path, 'r') as f:
        patterns = f.read().splitlines()

    return default_patterns + [p for p in patterns if p and not p.startswith('#')]

def is_ignored(path: str, ignore_patterns: List[str]) -> bool:
    """
    Checks if a given path should be ignored based on the ignore patterns.
    """
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def map_repo(directory: str, ignore_patterns: List[str], root_dir: str = None) -> Dict[str, Any]:
    """
    Recursively maps a directory, ignoring specified files and folders.
    """
    if root_dir is None:
        root_dir = directory

    repo_map = {'name': os.path.basename(directory), 'type': 'directory', 'children': []}

    for item in sorted(os.listdir(directory)):
        item_path = os.path.join(directory, item)
        relative_path = os.path.relpath(item_path, root_dir)

        # For matching gitignore-style patterns, ensure directories
        # are checked with a trailing slash.
        match_path = relative_path
        if os.path.isdir(item_path):
            match_path += '/'

        if is_ignored(match_path, ignore_patterns):
            continue

        if os.path.isdir(item_path):
            repo_map['children'].append(map_repo(item_path, ignore_patterns, root_dir))
        else:
            repo_map['children'].append({'name': item, 'type': 'file', 'path': relative_path})

    return repo_map

if __name__ == '__main__':
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Create a map of a software repository.")
    parser.add_argument('repo_path', type=str, help="The path to the repository to map.")
    parser.add_argument('--ignore-file', type=str, default='.gptignore', help="Path to the ignore file.")
    args = parser.parse_args()

    ignore_file = os.path.join(args.repo_path, args.ignore_file)
    ignore_patterns = get_ignore_patterns(ignore_file)

    repo_structure = map_repo(args.repo_path, ignore_patterns)

    print(json.dumps(repo_structure, indent=2))
