from pathlib import Path
from aider.watch import FileWatcher


def test_ai_comment_pattern():
    # Create a FileWatcher instance for testing
    watcher = FileWatcher(None)
    fixtures_dir = Path(__file__).parent.parent / "fixtures"

    # Test Python fixture
    py_path = fixtures_dir / "watch.py"
    py_lines, py_comments, py_has_bang = watcher.get_ai_comments(str(py_path))
    assert len(py_lines) == 11, f"Expected 11 AI comments in Python fixture, found {len(py_lines)}"
    assert py_has_bang, "Expected at least one bang (!) comment in Python fixture"

    # Test JavaScript fixture
    js_path = fixtures_dir / "watch.js"
    js_lines, js_comments, js_has_bang = watcher.get_ai_comments(str(js_path))
    assert len(js_lines) == 11, f"Expected 11 AI comments in JavaScript fixture, found {len(js_lines)}"
    assert js_has_bang, "Expected at least one bang (!) comment in JavaScript fixture"
