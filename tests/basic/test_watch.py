from pathlib import Path

from aider.watch import FileWatcher


def test_ai_comment_pattern():
    # Test various AI comment patterns
    test_comments = [
        "# ai do something",
        "# AI make this better",
        "# ai! urgent change needed",
        "# AI! another urgent one",
        "//ai javascript style",
        "//AI do that thing",
        "//ai! urgent js thing",
        "// ai with some space",
        "// AI with caps",
        "// ai! with bang",
    ]

    # Non-AI comments that shouldn't match
    non_ai_comments = [
        "# this is not an ai comment",
        "// this is also not an ai comment",
        "# aider is not an ai comment",
        "// aider is not an ai comment",
    ]

    # Test that all AI comments match
    for comment in test_comments:
        assert FileWatcher.ai_comment_pattern.search(comment), f"Should match: {comment}"

    # Test that non-AI comments don't match
    for comment in non_ai_comments:
        assert not FileWatcher.ai_comment_pattern.search(comment), f"Should not match: {comment}"
