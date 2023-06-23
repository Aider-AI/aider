import os
import shutil
import sys
from tempfile import TemporaryDirectory
from git import Repo
def create_temp_repo(dirname):
    with TemporaryDirectory() as tempdir:
        # Copy all files from dirname to tempdir
        for item in os.listdir(dirname):
            s = os.path.join(dirname, item)
            d = os.path.join(tempdir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, False, None)
            else:
                shutil.copy2(s, d)

        # Copy .docs subdir to tempdir as 'docs'
        docs_src = os.path.join(dirname, ".docs")
        docs_dst = os.path.join(tempdir, "docs")
        shutil.copytree(docs_src, docs_dst, False, None)

        # Create a new git repo in tempdir
        repo = Repo.init(tempdir)

        # Add all copied files to the repo
        repo.git.add(A=True)

        # Commit with message "initial"
        repo.git.commit(m="initial")

    return tempdir
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python benchmark.py <dirname>")
        sys.exit(1)

    dirname = sys.argv[1]
    temp_repo_path = create_temp_repo(dirname)
    print(f"Temporary repo created at: {temp_repo_path}")
