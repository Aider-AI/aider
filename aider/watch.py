from pathlib import Path
from typing import Optional, Set

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from watchfiles import watch

from aider.dump import dump  # noqa


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


def watch_source_files(
    directory: str, stop_event=None, gitignores: list[str] = None, ignore_func=None
) -> Set[str]:
    """
    Watch for changes to source files in the given directory and its subdirectories.
    Returns a set of changed file paths whenever changes are detected.

    Args:
        directory: Root directory to watch
        stop_event: Threading event to signal when to stop watching
        gitignores: List of paths to .gitignore files (optional)
        ignore_func: Optional function that takes a path (relative to watched directory)
                    and returns True if it should be ignored
    """
    root = Path(directory)

    gitignore_paths = [Path(g) for g in gitignores] if gitignores else []
    gitignore_spec = load_gitignores(gitignore_paths)
    root_abs = root.absolute()

    # Create a filter function that only accepts source files and respects gitignore
    def filter_func(change_type, path):
        path_obj = Path(path)
        path_abs = path_obj.absolute()

        if not path_abs.is_relative_to(root_abs):
            return False

        rel_path = path_abs.relative_to(root_abs)

        if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
            return False
        if ignore_func and ignore_func(rel_path):
            return False

        if not is_source_file(path_obj):
            return False

        # Check if file contains AI markers
        try:
            with open(path_abs) as f:
                content = f.read()
                import re

                return bool(re.search(r"(?:^|\n)(?:#|//) *ai\b", content, re.IGNORECASE))
        except (IOError, UnicodeDecodeError):
            return False

    # Watch the directory for changes
    for changes in watch(root, watch_filter=filter_func, stop_event=stop_event):
        # Convert the changes to a set of unique file paths
        changed_files = {str(Path(change[1])) for change in changes}
        yield changed_files


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
