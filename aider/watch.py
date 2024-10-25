from pathlib import Path
from typing import Set, Optional

from watchfiles import watch
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern


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


def load_gitignore(gitignore_path: Path) -> Optional[PathSpec]:
    """Load and parse a .gitignore file"""
    if not gitignore_path.exists():
        return None
        
    with open(gitignore_path) as f:
        patterns = f.readlines()
    
    return PathSpec.from_lines(GitWildMatchPattern, patterns)

def watch_source_files(directory: str, gitignore: str = None) -> Set[str]:
    """
    Watch for changes to source files in the given directory and its subdirectories.
    Returns a set of changed file paths whenever changes are detected.
    
    Args:
        directory: Root directory to watch
        gitignore: Path to .gitignore file (optional)
    """
    root = Path(directory)
    gitignore_spec = None
    
    if gitignore:
        gitignore_spec = load_gitignore(Path(gitignore))

    # Create a filter function that only accepts source files and respects gitignore
    def filter_func(change_type, path):
        path_obj = Path(path)
        if gitignore_spec and gitignore_spec.match_file(str(path_obj.relative_to(root))):
            return False
        return is_source_file(path_obj)

    # Watch the directory for changes
    for changes in watch(root, watch_filter=filter_func):
        # Convert the changes to a set of unique file paths
        changed_files = {str(Path(change[1])) for change in changes}
        yield changed_files


def main():
    """Example usage of the file watcher"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Watch source files for changes")
    parser.add_argument("directory", help="Directory to watch")
    parser.add_argument("--gitignore", help="Path to .gitignore file")
    args = parser.parse_args()

    directory = args.directory
    print(f"Watching source files in {directory}...")

    try:
        for changed_files in watch_source_files(directory, args.gitignore):
            print("\nChanged files:")
            for file in sorted(changed_files):
                print(f"  {file}")
    except KeyboardInterrupt:
        print("\nStopped watching files")


if __name__ == "__main__":
    main()
