import re
import threading
from pathlib import Path
from typing import Optional

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

    patterns = [".aider*", ".git"]  # Always ignore
    for path in gitignore_paths:
        if path.exists():
            with open(path) as f:
                patterns.extend(f.readlines())

    return PathSpec.from_lines(GitWildMatchPattern, patterns) if patterns else None


class FileWatcher:
    """Watches source files for changes and AI comments"""

    # Compiled regex pattern for AI comments
    ai_comment_pattern = re.compile(r"(?:#|//) *(ai\b.*|ai)", re.IGNORECASE)

    def __init__(self, coder, gitignores=None, verbose=False):
        self.coder = coder
        self.io = coder.io
        self.root = Path(coder.root)
        self.verbose = verbose  # or True
        self.stop_event = None
        self.watcher_thread = None
        self.changed_files = set()
        self.gitignores = gitignores

        coder.io.file_watcher = self

    def create_filter_func(self, gitignore_spec, ignore_func):
        """Creates a filter function for the file watcher"""

        def filter_func(change_type, path):
            path_obj = Path(path)
            path_abs = path_obj.absolute()

            if not path_abs.is_relative_to(self.root.absolute()):
                return False

            rel_path = path_abs.relative_to(self.root)
            if self.verbose:
                dump(rel_path)

            if gitignore_spec and gitignore_spec.match_file(str(rel_path)):
                return False
            if ignore_func and ignore_func(rel_path):
                return False

            if not is_source_file(path_obj):
                return False

            if self.verbose:
                dump("ok", rel_path)

            # Check if file contains AI markers
            try:
                content = self.io.read_text(str(path_abs))
                return self.ai_comment_pattern.search(content)
            except Exception as err:
                if self.verbose:
                    print("error")
                    dump(err)
                return False

        return filter_func

    def start(self, ignore_func=None):
        """Start watching for file changes"""
        self.stop_event = threading.Event()
        self.changed_files = set()

        gitignore_paths = [Path(g) for g in self.gitignores] if self.gitignores else []
        gitignore_spec = load_gitignores(gitignore_paths)
        filter_func = self.create_filter_func(gitignore_spec, ignore_func)

        def watch_files():
            try:
                for changes in watch(
                    str(self.root), watch_filter=filter_func, stop_event=self.stop_event
                ):
                    changed_files = {str(Path(change[1])) for change in changes}
                    result = {}
                    for file in changed_files:
                        if comments := self.get_ai_comment(file):
                            result[file] = comments

                    self.changed_files.update(result)
                    if self.verbose:
                        dump(result)
                        dump(self.changed_files)
                    if result:
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

        for fname in self.changed_files:
            # ai actually, check for bangs up here, not down below!
            if fname in self.coder.abs_fnames:
                continue
            self.coder.abs_fnames.add(fname)
            rel_fname = self.coder.get_rel_fname(fname)
            self.io.tool_output(f"Added {rel_fname} to the chat")
            self.io.tool_output()

        # Refresh all AI comments from tracked files
        ai_comments = {}
        has_bangs = False
        for fname in self.coder.abs_fnames:
            line_nums, comments, has_bang = self.get_ai_comments(fname)
            if line_nums:
                ai_comments[fname] = comments
                has_bangs |= has_bang

        if not has_bangs:
            return ""

        res = "\n".join(
            comment for comments in ai_comments.values() if comments for comment in comments
        )
        res = """The "ai" comments below can be found in the code files I've shared with you.
    They contain your instructions.
    Make the requested changes and remove all the "ai" comments from the code.

    """ + res

        dump(res)
        return res

    def get_ai_comments(self, filepath):
        """Extract AI comment line numbers, comments and bang status from a file"""
        line_nums = []
        comments = []
        has_bang = False
        content = self.io.read_text(filepath)
        for i, line in enumerate(content.splitlines(), 1):
            if match := self.ai_comment_pattern.search(line):
                comment = match.group(0).strip()
                if comment:
                    line_nums.append(i)
                    comments.append(comment)
                    if comment.strip().endswith("!"):
                        has_bang = True
        if not line_nums:
            return None, None, False
        return line_nums, comments, has_bang


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

    watcher = FileWatcher(directory)
    try:
        watcher.start(gitignores=args.gitignore, ignore_func=ignore_test_files)
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
