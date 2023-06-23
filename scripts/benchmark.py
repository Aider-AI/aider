import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

# from tempfile import TemporaryDirectory


def copy_exercise(dirname, tempdir):
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

    # Copy .docs subdir to tempdir as 'docs'
    docs_src = os.path.join(dirname, ".docs")
    docs_dst = os.path.join(tempdir, "docs")
    shutil.copytree(docs_src, docs_dst, False, None)

    return add_files


def main():
    if len(sys.argv) != 2:
        print("Usage: python benchmark.py <dirname>")
        sys.exit(1)

    dirname = Path(sys.argv[1])

    cwd = os.getcwd()

    total_tests = 0
    passed_tests = 0
    for testname in os.listdir(dirname):
        dump(testname)
        results = run_test(dirname / testname)
        os.chdir(cwd)

        if results:
            total_tests += 1
            passed = results["tests_passed"]
            if passed:
                passed_tests += 1

            dump(passed_tests, total_tests)


def run_test(testdir):
    if not os.path.isdir(testdir):
        print("Not a dir:", testdir)
        return

    os.chdir(testdir)

    started_fname = Path(".aider.started")
    if started_fname.exists():
        print(f"{testdir}/{started_fname} exists, skipping")
        return
    started_fname.touch()

    fnames = []
    for fname in os.listdir("."):
        if "test" not in fname and os.path.isfile(fname) and fname[0] != ".":
            fnames.append(fname)

    instructions = Path(".docs/instructions.md").read_text()
    instructions += (
        "\n\n=====\n\nModify these files according to the above instructions: " + " ".join(fnames)
    )

    io = InputOutput(
        pretty=True,
        yes=False,
    )

    main_model = models.Model("gpt-3.5-turbo")
    edit_format = main_model.edit_format

    coder = Coder.create(
        main_model,
        edit_format,
        io,
        os.environ["OPENAI_API_KEY"],
        fnames=fnames,
        # verbose=True,
        use_git=False,
        stream=False,
    )

    coder.run(with_message=instructions)

    passed = run_tests()

    results = dict(
        model=main_model.name,
        edit_format=edit_format,
        tests_passed=passed,
        cost=coder.total_cost,
    )
    dump(results)

    Path(".aider.results.json").write_text(json.dumps(results, indent=4))

    return results


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
    main()
