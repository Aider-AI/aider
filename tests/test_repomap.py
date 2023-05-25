import os
import unittest
from aider.repomap import RepoMap

class TestRepoMap(unittest.TestCase):
    def test_get_tags_map(self):
        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("")

            repo_map = RepoMap(root=temp_dir)
            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_tags_map(other_files)

            # Check if the result contains the expected tags map
            self.assertIn("test_file1.py:", result)
            self.assertIn("test_file2.py:", result)
            self.assertNotIn("test_file3.md:", result)
            self.assertNotIn("test_file4.json:", result)

if __name__ == "__main__":
    unittest.main()
