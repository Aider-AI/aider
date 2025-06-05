import pytest

from aider.sample_tool import concatenate_strings


def test_concatenate_strings_basic():
    """Test basic string concatenation."""
    result = concatenate_strings("Hello", "World")
    assert result == "HelloWorld"


def test_concatenate_strings_empty():
    """Test concatenation with empty strings."""
    assert concatenate_strings("", "") == ""
    assert concatenate_strings("Hello", "") == "Hello"
    assert concatenate_strings("", "World") == "World"


def test_concatenate_strings_with_spaces():
    """Test concatenation preserves spaces."""
    result = concatenate_strings("Hello ", "World")
    assert result == "Hello World"
