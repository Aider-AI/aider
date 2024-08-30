import os

import pytest

from aider.special import filter_important_files, is_important


def test_is_important():
    # Test common important files
    assert is_important("README.md")
    assert is_important(".gitignore")
    assert is_important("requirements.txt")
    assert is_important("setup.py")

    # Test files in .github/workflows
    assert is_important(os.path.join(".github", "workflows", "test.yml"))
    assert is_important(os.path.join(".github", "workflows", "deploy.yml"))

    # Test files that should not be considered important
    assert not is_important("random_file.txt")
    assert not is_important("src/main.py")
    assert not is_important("tests/test_app.py")


def test_filter_important_files():
    files = [
        "README.md",
        "src/main.py",
        ".gitignore",
        "tests/test_app.py",
        "requirements.txt",
        ".github/workflows/test.yml",
        "random_file.txt",
    ]

    important_files = filter_important_files(files)

    assert set(important_files) == {
        "README.md",
        ".gitignore",
        "requirements.txt",
        ".github/workflows/test.yml",
    }


def test_is_important_case_sensitivity():
    # Test case sensitivity
    assert is_important("README.md")
    assert not is_important("readme.md")
    assert is_important(".gitignore")
    assert not is_important(".GITIGNORE")


def test_is_important_with_paths():
    # Test with different path formats
    assert not is_important("project/README.md")
    assert is_important("./README.md")
    assert not is_important("/absolute/path/to/README.md")


@pytest.mark.parametrize(
    "file_path",
    [
        "README",
        "README.txt",
        "README.rst",
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "Dockerfile",
        "package.json",
        "pyproject.toml",
    ],
)
def test_is_important_various_files(file_path):
    assert is_important(file_path)
