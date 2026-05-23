import logging
from unittest import mock

from aider.repo import ANY_GIT_ERROR, GitRepo


def test_git_ignored_file_logs_debug_on_any_git_error():
    """Verify that debug logging fires when a programming exception
    is caught by except ANY_GIT_ERROR."""
    # Set up a minimal GitRepo-like object with a mock repo
    repo = mock.MagicMock()
    repo.ignored.side_effect = TypeError("simulated programming bug")

    git_repo = mock.MagicMock(spec=GitRepo)
    git_repo.repo = repo

    # Call the real method with our mocked object
    with mock.patch("aider.repo.logger") as mock_logger:
        result = GitRepo.git_ignored_file(git_repo, "somefile.py")

    assert result is False
    mock_logger.debug.assert_called_once()
    call_args = mock_logger.debug.call_args
    assert "TypeError" in str(call_args)
    assert "git_ignored_file" in str(call_args)
    assert call_args.kwargs.get("exc_info") is True
