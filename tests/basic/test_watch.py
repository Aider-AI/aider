from pathlib import Path

from aider.io import InputOutput
from aider.watch import FileWatcher


def test_ai_comment_pattern():
    # Create minimal IO and Coder instances for testing
    class MinimalCoder:
        def __init__(self, io):
            self.io = io
            self.root = "."
            self.abs_fnames = set()

        def get_rel_fname(self, fname):
            return fname

    io = InputOutput(pretty=False, fancy_input=False, yes=False)
    coder = MinimalCoder(io)
    watcher = FileWatcher(coder)
    fixtures_dir = Path(__file__).parent.parent / "fixtures"

    # Test Python fixture
    py_path = fixtures_dir / "watch.py"
    py_lines, py_comments, py_has_bang = watcher.get_ai_comments(str(py_path))

    # Count unique AI comments (excluding duplicates and variations with extra spaces)
    unique_py_comments = set(comment.strip().lower() for comment in py_comments)

    py_expected = 10
    assert len(unique_py_comments) == 10, (
        f"Expected {py_expected} unique AI comments in Python fixture, found"
        f" {len(unique_py_comments)}"
    )
    assert py_has_bang, "Expected at least one bang (!) comment in Python fixture"

    # Test JavaScript fixture
    js_path = fixtures_dir / "watch.js"
    js_lines, js_comments, js_has_bang = watcher.get_ai_comments(str(js_path))
    js_expected = 16
    assert (
        len(js_lines) == js_expected
    ), f"Expected {js_expected} AI comments in JavaScript fixture, found {len(js_lines)}"
    assert js_has_bang, "Expected at least one bang (!) comment in JavaScript fixture"
