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
    for file in os.listdir(tempdir):
        dump(file)
        full_path = os.path.join(tempdir, file)

        if "test" not in file and os.path.isfile(full_path):
            add_files.append(file)

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
    os.chdir(tempdir)

    instructions = Path("docs/instructions.md").read_text()

    instructions += (
        "\n\n=====\n\nModify these files according to the above instructions: " + " ".join(fnames)
    )

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
        # verbose=True,
        use_git=False,
        stream=False,
    )

    coder.run(with_message=instructions)

    run_tests()

import subprocess

def run_tests():
    test_files = [file for file in os.listdir() if "test" in file and file.endswith(".py")]
    all_tests_passed = True

    for test_file in test_files:
        result = subprocess.run(["python", test_file], capture_output=True, text=True)
        if result.returncode != 0:
            all_tests_passed = False
            print(f"Test {test_file} failed with the following output:\n{result.stderr}")

    return all_tests_passed

if __name__ == "__main__":
    # with TemporaryDirectory() as tempdir:
    tempdir = "tmp.benchmark"
    os.mkdir(tempdir)
    main(tempdir)
