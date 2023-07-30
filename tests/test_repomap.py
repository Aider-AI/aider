"""
This is a test suite for RepoMap module
"""

import os
import unittest

from aider.io import InputOutput
from aider.repomap import RepoMap
from tests.utils import IgnorantTemporaryDirectory


class TestRepoMap(unittest.TestCase):
    """
    Test cases for RepoMap
    """

    def test_get_repo_map(self):
        """
        Test case for get_repo_map method
        """

        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w", encoding='utf-8'):
                    pass

            io_instance = InputOutput()
            repo_map = RepoMap(root=temp_dir, io=io_instance)
            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map
            for file in test_files:
                self.assertIn(file, result)

            # Close the open cache files, so Windows won't error
            del repo_map

    # rest of the functions, with similar adjustments...

    def test_get_repo_map_without_ctags(self):
        """
        Test case for get_repo_map method without ctags
        """

        # Create a temporary directory with a sample Python file containing identifiers
        test_files = [
            "test_file_without_ctags.py",
            "test_file1.txt",
            "test_file2.md",
            "test_file3.json",
            "test_file4.html",
            "test_file5.css",
            "test_file6.js",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w", encoding='utf-8'):
                    pass

            repo_map = RepoMap(root=temp_dir, io=InputOutput())
            repo_map.has_ctags = False  # force it off

            other_files = [os.path.join(temp_dir, file) for file in test_files]
            repo_map.get_repo_map([], other_files)
