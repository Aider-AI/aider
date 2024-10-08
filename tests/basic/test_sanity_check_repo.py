import os
import shutil
import struct
from unittest import mock

import pytest
from git import GitError, Repo

from aider.main import sanity_check_repo


@pytest.fixture
def mock_io():
    """Fixture to create a mock io object."""
    return mock.Mock()


@pytest.fixture
def create_repo(tmp_path):
    """
    Fixture to create a standard Git repository.
    Returns the path to the repo and the Repo object.
    """
    repo_path = tmp_path / "test_repo"
    repo = Repo.init(repo_path)
    # Create an initial commit
    file_path = repo_path / "README.md"
    file_path.write_text("# Test Repository")
    repo.index.add([str(file_path.relative_to(repo_path))])
    repo.index.commit("Initial commit")
    return repo_path, repo


def set_git_index_version(repo_path, version):
    """
    Sets the Git index version by modifying the .git/index file.
    The index version is stored in the first 4 bytes as a little-endian integer.
    """
    index_path = os.path.join(repo_path, ".git", "index")
    with open(index_path, "r+b") as f:
        # Read the first 4 bytes (signature) and the next 4 bytes (version)
        signature = f.read(4)
        if signature != b"DIRC":
            raise ValueError("Invalid git index file signature.")
        # Write the new version
        f.seek(4)
        f.write(struct.pack("<I", version))


def detach_head(repo):
    """
    Detaches the HEAD of the repository by checking out the current commit hash.
    """
    current_commit = repo.head.commit
    repo.git.checkout(current_commit.hexsha)


def mock_repo_wrapper(repo_obj, git_repo_error=None):
    """
    Creates a mock 'repo' object to pass to sanity_check_repo.
    The mock object has:
    - repo.repo: the Repo object
    - repo.get_tracked_files(): returns a list of tracked files or raises GitError
    - repo.git_repo_error: the GitError if any
    """
    mock_repo = mock.Mock()
    mock_repo.repo = repo_obj
    if git_repo_error:

        def get_tracked_files_side_effect():
            raise git_repo_error

        mock_repo.get_tracked_files.side_effect = get_tracked_files_side_effect
        mock_repo.git_repo_error = git_repo_error
    else:
        mock_repo.get_tracked_files.return_value = [
            str(path) for path in repo_obj.git.ls_files().splitlines()
        ]
        mock_repo.git_repo_error = None
    return mock_repo


def test_detached_head_state(create_repo, mock_io):
    repo_path, repo = create_repo
    # Detach the HEAD
    detach_head(repo)

    # Create the mock 'repo' object
    mock_repo_obj = mock_repo_wrapper(repo)

    # Call the function
    result = sanity_check_repo(mock_repo_obj, mock_io)

    # Assert that the function returns True
    assert result is True

    # Assert that no errors were logged
    mock_io.tool_error.assert_not_called()
    mock_io.tool_output.assert_not_called()


def test_git_index_version_greater_than_2(create_repo, mock_io):
    repo_path, repo = create_repo
    # Set the git index version to 3
    set_git_index_version(str(repo_path), 3)

    # Simulate that get_tracked_files raises an error due to index version
    git_error = GitError("index version in (1, 2) is required")
    mock_repo_obj = mock_repo_wrapper(repo, git_repo_error=git_error)

    # Call the function
    result = sanity_check_repo(mock_repo_obj, mock_io)

    # Assert that the function returns False
    assert result is False

    # Assert that the appropriate error messages were logged
    mock_io.tool_error.assert_called_with(
        "Aider only works with git repos with version number 1 or 2."
    )
    mock_io.tool_error.assert_any_call(
        "Aider only works with git repos with version number 1 or 2."
    )
    mock_io.tool_output.assert_any_call(
        "You may be able to convert your repo: git update-index --index-version=2"
    )
    mock_io.tool_output.assert_any_call("Or run aider --no-git to proceed without using git.")
    mock_io.tool_output.assert_any_call("https://github.com/Aider-AI/aider/issues/211")


def test_bare_repository(create_repo, mock_io, tmp_path):
    # Initialize a bare repository
    bare_repo_path = tmp_path / "bare_repo.git"
    bare_repo = Repo.init(bare_repo_path, bare=True)

    # Create the mock 'repo' object
    mock_repo_obj = mock_repo_wrapper(bare_repo)

    # Call the function
    result = sanity_check_repo(mock_repo_obj, mock_io)

    # Assert that the function returns False
    assert result is False

    # Assert that the appropriate error message was logged
    mock_io.tool_error.assert_called_with("The git repo does not seem to have a working tree?")
    mock_io.tool_output.assert_not_called()


def test_sanity_check_repo_with_corrupt_repo(create_repo, mock_io):
    repo_path, repo = create_repo
    # Simulate a corrupt repository by removing the .git directory
    shutil.rmtree(os.path.join(repo_path, ".git"))

    # Create the mock 'repo' object with GitError
    git_error = GitError("Unable to read git repository, it may be corrupt?")
    mock_repo_obj = mock_repo_wrapper(repo, git_repo_error=git_error)

    # Call the function
    result = sanity_check_repo(mock_repo_obj, mock_io)

    # Assert that the function returns False
    assert result is False

    # Assert that the appropriate error messages were logged
    mock_io.tool_error.assert_called_with("Unable to read git repository, it may be corrupt?")
    mock_io.tool_output.assert_called_with(str(git_error))


def test_sanity_check_repo_with_no_repo(mock_io):
    # Call the function with repo=None
    result = sanity_check_repo(None, mock_io)

    # Assert that the function returns True
    assert result is True

    # Assert that no errors or outputs were logged
    mock_io.tool_error.assert_not_called()
    mock_io.tool_output.assert_not_called()
