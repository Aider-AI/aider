import unittest
from unittest.mock import MagicMock, patch

from aider.repo import GitRepo


class TestGitRepoPrompt(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo()
        self.repo.repo = MagicMock()
        self.repo.models = [MagicMock()]

    @patch("aider.repo.simple_send_with_retries")
    def test_commit_message_with_branch_template(self, mock_send):
        # Setup
        self.repo.repo.active_branch.name = "feature-123"
        self.repo.commit_prompt = "Generate commit for branch {{branch_name}}. Changes:"
        mock_send.return_value = "feat: add new feature"

        # Test
        result = self.repo.get_commit_message("some diff", "some context")

        # Verify
        self.assertEqual(result, "feat: add new feature")
        # Verify the template was substituted in the system content
        calls = mock_send.call_args_list
        self.assertEqual(len(calls), 1)
        messages = calls[0][0][1]
        self.assertEqual(messages[0]["content"], "Generate commit for branch feature-123. Changes:")
