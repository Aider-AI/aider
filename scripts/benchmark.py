import os
import shutil
import sys
from pathlib import Path

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

# from git import Repo


# from tempfile import TemporaryDirectory


def create_temp_repo(dirname, tempdir):
    # Copy all files from dirname to tempdir
    for item in os.listdir(dirname):
        s = os.path.join(dirname, item)
        d = os.path.join(tempdir, item)
        if os.path.isfile(s):
            shutil.copy2(s, d)

    add_files = []
    for root, _, files in os.walk(tempdir):
        for file in files:
            if "test" not in file:
                rel_path = os.path.relpath(os.path.join(root, file), tempdir)
                add_files.append(rel_path)

    """
    # Create a new git repo in tempdir
    repo = Repo.init(tempdir)

    for rel_path in add_files:
        repo.git.add(rel_path)

    # Commit with message "initial"
    repo.git.commit(m="initial")
    """

    # Copy .docs subdir to tempdir as 'docs'
    docs_src = os.path.join(dirname, ".docs")
    docs_dst = os.path.join(tempdir, "docs")
    shutil.copytree(docs_src, docs_dst, False, None)

    return add_files


def main(tempdir):
    if len(sys.argv) != 2:
        print("Usage: python benchmark.py <dirname>")
        sys.exit(1)

    dirname = sys.argv[1]

    fnames = create_temp_repo(dirname, tempdir)
    tempdir = Path(tempdir)
    fnames = [tempdir / fn for fn in fnames]

    io = InputOutput(
        pretty=True,
        yes=False,
    )

    main_model = models.Model("gpt-3.5-turbo")

    coder = Coder.create(
        main_model,
        None,
        io,
        os.environ["OPENAI_API_KEY"],
        fnames=fnames,
        verbose=True,
        git=False,
    )

    coder.run(with_message="follow the instructions in the .md file")


if __name__ == "__main__":
    # with TemporaryDirectory() as tempdir:
    tempdir = "tmp.benchmark"
    os.mkdir(tempdir)
    main(tempdir)
