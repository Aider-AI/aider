import os
from pathlib import Path

class Coder:
    def __init__(self):
        pass

    def get_all_files(self):
        files = []
        start_dir = os.getcwd()
        repo_root = self.find_git_root(start_dir)

        for root, dirs, filenames in os.walk(start_dir, topdown=True):
            # Exclude directories starting with a dot
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            # Exclude .venv directory at the repo root
            dirs[:] = [d for d in dirs if not (os.path.join(repo_root, d) == os.path.join(repo_root, '.venv'))]

            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files

    def find_git_root(self, path):
        git_root = Path(path).resolve()
        while git_root != git_root.parent:
            if (git_root / '.git').is_dir():
                return str(git_root)
            git_root = git_root.parent
        return None
