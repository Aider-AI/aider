import re
from pathlib import Path
from typing import Optional, Set

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from watchfiles import watch

from aider.dump import dump  # noqa

VERBOSE = False


def is_source_file(path: Path) -> bool:
    """
    Check if a file is a source file that uses # or // style comments.
    This includes Python, JavaScript, TypeScript, C, C++, etc.
    """
    COMMENT_STYLE_EXTENSIONS = {
        # # style comments
        ".py",
        ".r",
        ".rb",
        ".pl",
        ".pm",
        ".sh",
        ".bash",
        ".yaml",
        ".yml",
        # // style comments
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".java",
        ".swift",
        ".kt",
        ".cs",
        ".go",
        ".rs",
        ".php",
    }
    return path.suffix.lower() in COMMENT_STYLE_EXTENSIONS


def load_gitignores(gitignore_paths: list[Path]) -> Optional[PathSpec]:
    """Load and parse multiple .gitignore files into a single PathSpec"""
    if not gitignore_paths:
        return None

    patterns = []
    for path in gitignore_paths:
        if path.exists():
            with open(path) as f:
                patterns.extend(f.readlines())

    return PathSpec.from_lines(GitWildMatchPattern, patterns) if patterns else None


class FileWatcher:
    """Watches source files for changes and AI comments"""
    
    def __init__(self, directory: str, encoding="utf-8"):
        self.directory = directory
        self.encoding = encoding
        self.root = Path(directory)
        self.root_abs = self.root.absolute()
        self.stop_event = None
        self.watcher_thread = None
        self.changed_files = None

    def create_filter_func(self, gitignore_spec, ignore_func):
        """Creates a filter function for the file watcher"""
        def filter_func(change_type, path):
            path_obj = Path(path)
            path_abs = path_obj.absolute()

            if not path_abs.is_relative_to(self.root_abs):
                return False

            rel_path = path_abs.relative_to(self.root_abs)
            if VERBOSE:
                dump(rel_path)

            if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
                return False
            if ignore_func and ignore_func(rel_path):
                return False

            if not is_source_file(path_obj):
                return False

            if VERBOSE:
                dump("ok", rel_path)

            # Check if file contains AI markers
            try:
                with open(path_abs, encoding=self.encoding, errors="ignore") as f:
                    content = f.read()

                    res = bool(re.search(r"(?:#|//) *ai\b", content, re.IGNORECASE))
                    if VERBOSE:
                        dump(res)
                    return res
            except (IOError, UnicodeDecodeError) as err:
                if VERBOSE:
                    dump(err)
                return False

        return filter_func

    def start(self, gitignores: list[str] = None, ignore_func=None):
        """Start watching for file changes"""
        self.stop_event = threading.Event()
        
        gitignore_paths = [Path(g) for g in gitignores] if gitignores else []
        gitignore_spec = load_gitignores(gitignore_paths)
        filter_func = self.create_filter_func(gitignore_spec, ignore_func)

        def watch_files():
            try:
                for changes in watch(self.root, watch_filter=filter_func, stop_event=self.stop_event):
                    changed_files = {str(Path(change[1])) for change in changes}
                    result = {}
                    for file in changed_files:
                        if comments := get_ai_comment(file, encoding=self.encoding):
                            result[file] = comments

                    if VERBOSE:
                        dump(result)
                    if result:
                        self.changed_files = result
                        return
            except Exception as e:
                if VERBOSE:
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

    def get_changes(self):
        """Get any detected file changes"""
        return self.changed_files


def get_ai_comment(filepath, encoding="utf-8"):
    """Extract all AI comments from a file"""
    comments = []
    try:
        with open(filepath, encoding=encoding, errors="ignore") as f:
            for line in f:
                if match := re.search(r"(?:#|//) *(ai\b.*|ai)", line, re.IGNORECASE):
                    comment = match.group(0).strip()
                    if comment:
                        comments.append(comment)
    except (IOError, UnicodeDecodeError):
        return None
    return comments if comments else None


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

    try:
        for changed_files in watch_source_files(
            directory, args.gitignore, ignore_func=ignore_test_files
        ):
            for file in sorted(changed_files):
                print(file)
    except KeyboardInterrupt:
        print("\nStopped watching files")


if __name__ == "__main__":
    main()
