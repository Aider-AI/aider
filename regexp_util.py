import re

def foo_not_followed_by_close_paren():
    """
    Returns a regular expression pattern that matches 'foo' not followed by a closing parenthesis.
    
    The pattern uses negative lookahead (?!) to assert that what follows is not a closing parenthesis.
    """
    pattern = r'foo(?!\))'
    return pattern

def test_pattern():
    """Test the pattern with various examples"""
    pattern = foo_not_followed_by_close_paren()
    regex = re.compile(pattern)
    
    # Should match
    assert regex.search("foo bar")
    assert regex.search("foobar")
    assert regex.search("foo(bar")
    
    # Should not match
    assert not regex.search("bar")
    assert regex.search("foo)") is not None  # Matches because ) is after foo, not directly after
    assert regex.search("foo)bar") is not None  # Same reason
    assert not regex.search("(foo)")  # Doesn't match because foo is followed by )
    
    print("All tests passed!")

if __name__ == "__main__":
    print(f"Pattern: {foo_not_followed_by_close_paren()}")
    test_pattern()
