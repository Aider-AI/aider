from pathlib import Path
from typing import Set

from watchfiles import watch


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


def watch_source_files(directory: str) -> Set[str]:
    """
    Watch for changes to source files in the given directory and its subdirectories.
    Returns a set of changed file paths whenever changes are detected.
    """
    root = Path(directory)

    # Create a filter function that only accepts source files
    def filter_func(change_type, path):
        return is_source_file(Path(path))

    # Watch the directory for changes
    for changes in watch(root, watch_filter=filter_func):
        # Convert the changes to a set of unique file paths
        changed_files = {str(Path(change[1])) for change in changes}
        yield changed_files


def main():
    """Example usage of the file watcher"""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python watch.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    print(f"Watching source files in {directory}...")

    try:
        for changed_files in watch_source_files(directory):
            print("\nChanged files:")
            for file in sorted(changed_files):
                print(f"  {file}")
    except KeyboardInterrupt:
        print("\nStopped watching files")


if __name__ == "__main__":
    main()
