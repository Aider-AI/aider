import re
import threading
from pathlib import Path
from typing import Optional

from grep_ast import TreeContext
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from watchfiles import watch

from aider.dump import dump  # noqa
from aider.comment_processor import CommentProcessor


def load_gitignores(gitignore_paths: list[Path]) -> Optional[PathSpec]:
    """Load and parse multiple .gitignore files into a single PathSpec"""
    if not gitignore_paths:
        return None

    patterns = [
        ".aider*",
        ".git",
        # Common editor backup/temp files
        "*~",  # Emacs/vim backup
        "*.bak",  # Generic backup
        "*.swp",  # Vim swap
        "*.swo",  # Vim swap
        "\\#*\\#",  # Emacs auto-save
        ".#*",  # Emacs lock files
        "*.tmp",  # Generic temp files
        "*.temp",  # Generic temp files
        "*.orig",  # Merge conflict originals
        "*.pyc",  # Python bytecode
        "__pycache__/",  # Python cache dir
        ".DS_Store",  # macOS metadata
        "Thumbs.db",  # Windows thumbnail cache
        # IDE files
        ".idea/",  # JetBrains IDEs
        ".vscode/",  # VS Code
        "*.sublime-*",  # Sublime Text
        ".project",  # Eclipse
        ".settings/",  # Eclipse
        "*.code-workspace",  # VS Code workspace
        # Environment files
        ".env",  # Environment variables
        ".venv/",  # Python virtual environments
        "node_modules/",  # Node.js dependencies
        "vendor/",  # Various dependencies
        # Logs and caches
        "*.log",  # Log files
        ".cache/",  # Cache directories
        ".pytest_cache/",  # Python test cache
        "coverage/",  # Code coverage reports
    ]  # Always ignore
    for path in gitignore_paths:
        if path.exists():
            with open(path) as f:
                patterns.extend(f.readlines())

    return PathSpec.from_lines(GitWildMatchPattern, patterns) if patterns else None


class FileWatcher:
    """Watches source files for changes and AI comments"""

    # Compiled regex pattern for AI comments
    ai_comment_pattern = re.compile(r"(?:#|//|--) *(ai\b.*|ai\b.*|.*\bai[?!]?) *$", re.IGNORECASE)

    def __init__(self, coder, gitignores=None, verbose=False, analytics=None, root=None):
        self.coder = coder
        self.io = coder.io
        self.root = Path(root) if root else Path(coder.root)
        self.verbose = verbose
        self.analytics = analytics
        self.stop_event = None
        self.watcher_thread = None
        self.changed_files = set()
        self.gitignores = gitignores

        self.gitignore_spec = load_gitignores(
            [Path(g) for g in self.gitignores] if self.gitignores else []
        )

        self.comment_processor = CommentProcessor(self.io, self.coder, self.analytics)
        coder.io.file_watcher = self

    def filter_func(self, change_type, path):
        """Filter function for the file watcher"""
        path_obj = Path(path)
        path_abs = path_obj.absolute()

        if not path_abs.is_relative_to(self.root.absolute()):
            return False

        rel_path = path_abs.relative_to(self.root)
        if self.verbose:
            dump(rel_path)

        if self.gitignore_spec and self.gitignore_spec.match_file(str(rel_path)):
            return False

        if self.verbose:
            dump("ok", rel_path)

        # Check if file contains AI markers
        try:
            comments, _, _ = self.comment_processor.get_ai_comments(str(path_abs))
            return bool(comments)
        except Exception:
            return

    def start(self):
        """Start watching for file changes"""
        self.stop_event = threading.Event()
        self.changed_files = set()

        def watch_files():
            try:
                for changes in watch(
                    str(self.root), watch_filter=self.filter_func, stop_event=self.stop_event
                ):
                    if not changes:
                        continue
                    changed_files = {str(Path(change[1])) for change in changes}
                    self.changed_files.update(changed_files)
                    if self.io.prompt_session and self.io.prompt_session.app:
                        self.io.interrupt_input()
                    return
            except Exception as e:
                if self.verbose:
                    dump(f"File watcher error: {e}")
                raise e

        self.watcher_thread = threading.Thread(target=watch_files, daemon=True)
        self.watcher_thread.start()

    def stop(self):
        """Stop watching for file changes"""
        if self.stop_event:
            self.stop_event.set()
        if self.watcher_thread:
            self.watcher_thread.join()
            self.watcher_thread = None
            self.stop_event = None

    def process_changes(self):
        """Get any detected file changes"""
        return self.comment_processor.process_changes(self.changed_files)

def main():
    """Example usage of the file watcher"""
    import argparse

    parser = argparse.ArgumentParser(description="Watch source files for changes")
    parser.add_argument("directory", help="Directory to watch")
    parser.add_argument(
        "--gitignore",
        action="append",
        help="Path to .gitignore file (can be specified multiple times)",
    )
    args = parser.parse_args()

    directory = args.directory
    print(f"Watching source files in {directory}...")

    # Example ignore function that ignores files with "test" in the name
    def ignore_test_files(path):
        return "test" in path.name.lower()

    watcher = FileWatcher(directory, gitignores=args.gitignore)
    try:
        watcher.start()
        while True:
            if changes := watcher.get_changes():
                for file in sorted(changes.keys()):
                    print(file)
                watcher.changed_files = None
    except KeyboardInterrupt:
        print("\nStopped watching files")
        watcher.stop()


if __name__ == "__main__":
    main()
