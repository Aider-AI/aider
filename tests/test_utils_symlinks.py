import os
import unittest
from pathlib import Path
import tempfile

from aider.utils import safe_abs_path


class TestUtilsSymlinks(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for our tests
        self.test_dir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        # Clean up
        os.chdir(self.orig_cwd)
        try:
            import shutil
            shutil.rmtree(self.test_dir)
        except:
            pass

    def test_safe_abs_path_normal(self):
        """Test safe_abs_path with a normal path"""
        test_file = Path(self.test_dir) / "test.txt"
        test_file.touch()
        result = safe_abs_path(test_file)
        self.assertEqual(str(test_file.resolve()), result)

    def test_safe_abs_path_symlink_loop(self):
        """Test safe_abs_path with a circular symlink"""
        # Create a circular symlink
        link1 = Path(self.test_dir) / "link1"
        link2 = Path(self.test_dir) / "link2"
        
        # Create the first link pointing to the second
        os.symlink("link2", str(link1))
        # Create the second link pointing back to the first
        os.symlink("link1", str(link2))

        # Test that safe_abs_path handles the symlink loop gracefully
        result = safe_abs_path(link1)
        self.assertTrue(result.endswith("link1"))
        self.assertTrue(os.path.isabs(result))

    def test_safe_abs_path_nonexistent(self):
        """Test safe_abs_path with a non-existent path"""
        nonexistent = Path(self.test_dir) / "nonexistent"
        result = safe_abs_path(nonexistent)
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(result.endswith("nonexistent"))

    def test_safe_abs_path_relative(self):
        """Test safe_abs_path with a relative path"""
        rel_path = "relative/path"
        result = safe_abs_path(rel_path)
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(result.endswith(rel_path.replace("/", os.path.sep)))