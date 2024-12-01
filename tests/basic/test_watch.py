from pathlib import Path

from aider.watch import FileWatcher


def test_ai_comment_pattern():
    # Read fixture files
    fixtures_dir = Path(__file__).parent.parent / "fixtures"

    with open(fixtures_dir / "watch.py") as f:
        py_content = f.read()
    with open(fixtures_dir / "watch.js") as f:
        js_content = f.read()

    # Count AI comments in Python fixture
    py_matches = 0
    for line in py_content.splitlines():
        if FileWatcher.ai_comment_pattern.search(line):
            py_matches += 1
    assert py_matches == 11, f"Expected 11 AI comments in Python fixture, found {py_matches}"

    # Count AI comments in JavaScript fixture
    js_matches = 0
    for line in js_content.splitlines():
        if FileWatcher.ai_comment_pattern.search(line):
            js_matches += 1
    assert js_matches == 11, f"Expected 11 AI comments in JavaScript fixture, found {js_matches}"
