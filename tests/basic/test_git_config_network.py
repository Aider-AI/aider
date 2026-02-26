import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, MagicMock

import git

from aider.io import InputOutput
from aider.main import setup_git
from aider.utils import GitTemporaryDirectory


class TestGitConfigNetworkDrive(TestCase):
    def setUp(self):
        self.tempdir = GitTemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tempdir.cleanup()

    def test_setup_git_with_permission_error(self):
        """Test that setup_git handles permission errors gracefully"""
        io = InputOutput(pretty=False, yes=True)

        # Create a mock repo that raises PermissionError on config_writer
        mock_repo = MagicMock(spec=git.Repo)
        mock_config_writer = MagicMock()
        mock_config_writer.__enter__ = MagicMock(side_effect=PermissionError("Permission denied"))
        mock_repo.config_writer.return_value = mock_config_writer
        
        # Create a test working directory to return
        test_dir = str(Path(self.tempdir.name).resolve())
        mock_repo.working_tree_dir = test_dir

        # Mock git.Repo to return our mock
        with patch('git.Repo', return_value=mock_repo):
            result = setup_git(test_dir, io)

        # Verify setup_git completes and returns working directory despite error
        self.assertEqual(result, test_dir)

        # Verify warning was shown
        warnings = [call[0][0] for call in io.tool_warning.call_args_list]
        self.assertTrue(any("Could not write to git config" in warning for warning in warnings))