from pathlib import Path

from aider.dump import dump  # noqa
from aider.io import InputOutput
from aider.watch import FileWatcher


class MinimalCoder:
    def __init__(self, io):
        self.io = io
        self.root = "."
        self.abs_fnames = set()

    def get_rel_fname(self, fname):
        return fname


def test_gitignore_patterns():
    """Test that gitignore patterns are properly loaded and matched"""
    from pathlib import Path

    from aider.watch import load_gitignores

    # Create a temporary gitignore file with test patterns
    tmp_gitignore = Path("test.gitignore")
    tmp_gitignore.write_text("custom_pattern\n*.custom")

    gitignores = [tmp_gitignore]
    spec = load_gitignores(gitignores)

    # Test built-in patterns
    assert spec.match_file(".aider.conf")
    assert spec.match_file(".git/config")
    assert spec.match_file("file~")  # Emacs/vim backup
    assert spec.match_file("file.bak")
    assert spec.match_file("file.swp")
    assert spec.match_file("file.swo")
    assert spec.match_file("#temp#")  # Emacs auto-save
    assert spec.match_file(".#lock")  # Emacs lock
    assert spec.match_file("temp.tmp")
    assert spec.match_file("temp.temp")
    assert spec.match_file("conflict.orig")
    assert spec.match_file("script.pyc")
    assert spec.match_file("__pycache__/module.pyc")
    assert spec.match_file(".DS_Store")
    assert spec.match_file("Thumbs.db")
    assert spec.match_file(".idea/workspace.xml")
    assert spec.match_file(".vscode/settings.json")
    assert spec.match_file("project.sublime-workspace")
    assert spec.match_file(".project")
    assert spec.match_file(".settings/config.json")
    assert spec.match_file("workspace.code-workspace")
    assert spec.match_file(".env")
    assert spec.match_file(".venv/bin/python")
    assert spec.match_file("node_modules/package/index.js")
    assert spec.match_file("vendor/lib/module.py")
    assert spec.match_file("debug.log")
    assert spec.match_file(".cache/files")
    assert spec.match_file(".pytest_cache/v/cache")
    assert spec.match_file("coverage/lcov.info")

    # Test custom patterns from gitignore file
    assert spec.match_file("custom_pattern")
    assert spec.match_file("file.custom")

    # Test non-matching patterns
    assert not spec.match_file("regular_file.txt")
    assert not spec.match_file("src/main.py")
    assert not spec.match_file("docs/index.html")

    # Cleanup
    tmp_gitignore.unlink()


def test_get_roots_to_watch(tmp_path):
    # Create a test directory structure
    (tmp_path / "included").mkdir()
    (tmp_path / "excluded").mkdir()

    io = InputOutput(pretty=False, fancy_input=False, yes=False)
    coder = MinimalCoder(io)

    # Test with no gitignore
    watcher = FileWatcher(coder, root=tmp_path)
    roots = watcher.get_roots_to_watch()
    assert len(roots) == 1
    assert roots[0] == str(tmp_path)

    # Test with gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("excluded/")
    watcher = FileWatcher(coder, root=tmp_path, gitignores=[gitignore])
    roots = watcher.get_roots_to_watch()
    assert len(roots) == 2
    assert Path(sorted(roots)[0]).name == ".gitignore"
    assert Path(sorted(roots)[1]).name == "included"


def test_handle_changes():
    io = InputOutput(pretty=False, fancy_input=False, yes=False)
    coder = MinimalCoder(io)
    watcher = FileWatcher(coder)

    # Test no changes
    assert not watcher.handle_changes([])
    assert len(watcher.changed_files) == 0

    # Test with changes
    changes = [("modified", "/path/to/file.py")]
    assert watcher.handle_changes(changes)
    assert len(watcher.changed_files) == 1
    assert str(Path("/path/to/file.py")) in watcher.changed_files


def test_ai_comment_pattern():
    # Create minimal IO and Coder instances for testing
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
    assert py_has_bang == "!", "Expected at least one bang (!) comment in Python fixture"

    # Test JavaScript fixture
    js_path = fixtures_dir / "watch.js"
    js_lines, js_comments, js_has_bang = watcher.get_ai_comments(str(js_path))
    js_expected = 16
    assert (
        len(js_lines) == js_expected
    ), f"Expected {js_expected} AI comments in JavaScript fixture, found {len(js_lines)}"
    assert js_has_bang == "!", "Expected at least one bang (!) comment in JavaScript fixture"

    # Test watch_question.js fixture
    question_js_path = fixtures_dir / "watch_question.js"
    question_js_lines, question_js_comments, question_js_has_bang = watcher.get_ai_comments(
        str(question_js_path)
    )
    question_js_expected = 6
    assert len(question_js_lines) == question_js_expected, (
        f"Expected {question_js_expected} AI comments in watch_question.js fixture, found"
        f" {len(question_js_lines)}"
    )
    assert (
        question_js_has_bang == "?"
    ), "Expected at least one bang (!) comment in watch_question.js fixture"
    
    # Test Lisp fixture
    lisp_path = fixtures_dir / "watch.lisp"
    lisp_lines, lisp_comments, lisp_has_bang = watcher.get_ai_comments(str(lisp_path))
    lisp_expected = 7
    assert (
        len(lisp_lines) == lisp_expected
    ), f"Expected {lisp_expected} AI comments in Lisp fixture, found {len(lisp_lines)}"
    assert lisp_has_bang == "!", "Expected at least one bang (!) comment in Lisp fixture"
