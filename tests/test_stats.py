import unittest
import subprocess
from unittest.mock import patch, MagicMock
from collections import defaultdict

from aider.stats import (
    get_all_commit_hashes_between_tags,
    get_commit_authors,
    get_counts_for_file,
    hash_len,
)


class TestStats(unittest.TestCase):
    @patch("aider.stats.run")
    def test_get_all_commit_hashes_between_tags(self, mock_run):
        # Test with end_tag
        mock_run.return_value = "commit1\ncommit2\ncommit3"
        result = get_all_commit_hashes_between_tags("v1.0.0", "v2.0.0")
        mock_run.assert_called_with(["git", "rev-list", "v1.0.0..v2.0.0"])
        self.assertEqual(result, ["commit1", "commit2", "commit3"])

        # Test without end_tag (defaults to HEAD)
        mock_run.return_value = "commit4\ncommit5"
        result = get_all_commit_hashes_between_tags("v1.0.0")
        mock_run.assert_called_with(["git", "rev-list", "v1.0.0..HEAD"])
        self.assertEqual(result, ["commit4", "commit5"])

        # Test with empty result
        mock_run.return_value = ""
        result = get_all_commit_hashes_between_tags("v1.0.0", "v1.0.0")
        self.assertEqual(result, None)

    @patch("aider.stats.run")
    def test_get_commit_authors(self, mock_run):
        # Setup mock responses for git show commands
        def mock_run_side_effect(cmd):
            if cmd[0:3] == ["git", "show", "-s"]:
                if "--format=%an" in cmd:
                    if cmd[-1] == "commit1":
                        return "Author1\n"
                    elif cmd[-1] == "commit2":
                        return "Author2\n"
                elif "--format=%s" in cmd:
                    if cmd[-1] == "commit1":
                        return "Normal commit message\n"
                    elif cmd[-1] == "commit2":
                        return "aider: AI generated commit\n"
            return ""

        mock_run.side_effect = mock_run_side_effect
        
        # Test author attribution with aider tag
        commits = ["commit1", "commit2"]
        result = get_commit_authors(commits)
        
        expected = {
            "commit1": "Author1",
            "commit2": "Author2 (aider)",
        }
        self.assertEqual(result, expected)

    @patch("aider.stats.run")
    def test_get_counts_for_file(self, mock_run):
        # Setup mock for git blame
        blame_output = f"""
{hash_len * '0'} (Author1 2023-01-01 12:00:00 +0000 1) Line 1
{hash_len * '1'} (Author2 2023-01-02 12:00:00 +0000 2) Line 2
{hash_len * '1'} (Author2 2023-01-02 12:00:00 +0000 3) Line 3
^{hash_len * '2'} (Author3 2023-01-03 12:00:00 +0000 4) Line 4 (not counted - from before start_tag)
"""
        mock_run.return_value = blame_output.strip()
        
        # Mock authors dictionary
        authors = {
            "0" * hash_len: "Author1",
            "1" * hash_len: "Author2 (aider)",
        }
        
        # Test with end_tag
        result = get_counts_for_file("v1.0.0", "v2.0.0", authors, "test_file.py")
        mock_run.assert_called_with([
            "git", "blame", "-M", "-C", "-C", "--abbrev=9", 
            "v1.0.0..v2.0.0", "--", "test_file.py"
        ])
        
        expected = {
            "Author1": 1,
            "Author2 (aider)": 2,
        }
        self.assertEqual(result, expected)
        
        # Test with no end_tag
        result = get_counts_for_file("v1.0.0", None, authors, "test_file.py")
        mock_run.assert_called_with([
            "git", "blame", "-M", "-C", "-C", "--abbrev=9", 
            "v1.0.0..HEAD", "--", "test_file.py"
        ])

    @patch("aider.stats.run")
    def test_get_counts_for_file_error_handling(self, mock_run):
        # Test file not found error
        error = subprocess.CalledProcessError(1, "git blame", stderr=b"no such path 'nonexistent.py'")
        mock_run.side_effect = error
        
        result = get_counts_for_file("v1.0.0", "v2.0.0", {}, "nonexistent.py")
        self.assertIsNone(result)
        
        # Test other git error
        error = subprocess.CalledProcessError(1, "git blame", stderr=b"some other git error")
        mock_run.side_effect = error
        
        with patch("sys.stderr"):  # Suppress stderr output during test
            result = get_counts_for_file("v1.0.0", "v2.0.0", {}, "test_file.py")
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
