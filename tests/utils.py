import os
import tempfile

import git

from aider.dump import dump  # noqa: F401


class IgnorantTemporaryDirectory:
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.temp_dir.__exit__(exc_type, exc_val, exc_tb)
        except OSError:
            pass  # Ignore errors (Windows)


class ChdirTemporaryDirectory(IgnorantTemporaryDirectory):
    def __init__(self):
        self.cwd = os.getcwd()
        super().__init__()

    def __enter__(self):
        res = super().__enter__()
        os.chdir(self.temp_dir.name)
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.cwd)
        super().__exit__(exc_type, exc_val, exc_tb)


class GitTemporaryDirectory(ChdirTemporaryDirectory):
    def __enter__(self):
        res = super().__enter__()
        make_repo()
        return res


def make_repo():
    repo = git.Repo.init()
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "testuser@example.com").release()
