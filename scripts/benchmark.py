import argparse
import datetime
import json
import os
import shutil
import subprocess
import time
from json.decoder import JSONDecodeError
from pathlib import Path

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

ORIGINAL_DNAME = Path("tmp.benchmark/practice")
assert ORIGINAL_DNAME.exists()


def main():
    parser = argparse.ArgumentParser(description="Aider Benchmark")
    parser.add_argument("dirname", type=str, help="Directory name")
    parser.add_argument("--model", "-m", type=str, help="Model name", default="gpt-3.5-turbo")
    parser.add_argument("--edit-format", "-e", type=str, help="Edit format")
    parser.add_argument("--keyword", "-k", type=str, help="Only run tests that contain keyword")
    parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="Discard the current testdir and make a clean copy",
    )
    parser.add_argument(
        "--retries",
        "-r",
        type=int,
        help="Number of retries for running tests",
        default=2,
    )

    args = parser.parse_args()

    dirname = Path(args.dirname)

    if args.clean and dirname.exists():
        print("Cleaning up and replacing", dirname)
        dir_files = set(fn.name for fn in dirname.glob("*"))
        original_files = set(fn.name for fn in ORIGINAL_DNAME.glob("*"))
        if dir_files != original_files:
            print("ERROR: will not delete dir that does not look like original tests", dirname)
            return

        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S-")
        dest = dirname.parent / "OLD" / (now + dirname.name)
        dirname.rename(dest)

    if not dirname.exists():
        shutil.copytree(ORIGINAL_DNAME, dirname)

    cwd = os.getcwd()

    test_dnames = sorted(os.listdir(dirname))

    total_tests = len(test_dnames)
    completed_tests = 0
    passed_tests = 0

    total_cost = 0

    for testname in test_dnames:
        if args.keyword and args.keyword not in testname:
            continue

        dump(testname)
        results = run_test(dirname / testname, args.model, args.edit_format, args.retries)
        os.chdir(cwd)

        if results:
            completed_tests += 1
            passed = results["tests_outcomes"][-1]
            if passed:
                passed_tests += 1

            dump(passed_tests, completed_tests, total_tests)

            pass_rate = 100 * passed_tests / completed_tests
            dump(pass_rate)

            total_cost += results["cost"]
            dump(total_cost)

            projected_cost = total_cost * total_tests / completed_tests
            dump(projected_cost)

            print()

        ###
        # input('next?')


def run_test(testdir, model_name, edit_format, retries):
    if not os.path.isdir(testdir):
        print("Not a dir:", testdir)
        return

    os.chdir(testdir)

    history_fname = Path(".aider.chat.history.md")

    results_fname = Path(".aider.results.json")
    if results_fname.exists():
        try:
            return json.loads(results_fname.read_text())
        except JSONDecodeError:
            print(f"{testdir}/{results_fname} failed to parse, skipping")
            return

    started_fname = Path(".aider.started")
    if started_fname.exists():
        # print(f"{testdir}/{started_fname} exists, skipping")
        # return
        pass
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
        chat_history_file=history_fname,
    )

    main_model = models.Model(model_name)
    edit_format = edit_format or main_model.edit_format

    dump(main_model)
    dump(edit_format)

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

    dur = 0
    test_outcomes = []
    for i in range(retries):
        start = time.time()
        coder.run(with_message=instructions)
        dur += time.time() - start

        if coder.num_control_c:
            raise KeyboardInterrupt

        errors = run_tests(history_fname)

        if errors:
            test_outcomes.append(False)
        else:
            test_outcomes.append(True)
            break

        instructions = errors
        filelist = " ".join(fnames)
        instructions += f"\n\nFix the code in {filelist} to resolve the errors above."

    results = dict(
        testdir=str(testdir),
        model=main_model.name,
        edit_format=edit_format,
        tests_outcomes=test_outcomes,
        cost=coder.total_cost,
        duration=dur,
    )
    dump(results)

    results_fname.write_text(json.dumps(results, indent=4))
    started_fname.unlink()

    return results


def run_tests(history_fname):
    test_files = [file for file in os.listdir() if file.endswith("_test.py")]
    assert len(test_files)

    all_tests_passed = True
    timeout = 60
    for test_file in test_files:
        dump(test_file)
        try:
            result = subprocess.run(
                ["pytest", test_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                all_tests_passed = False
                print(f"Test {test_file} failed with the following output:\n{result.stderr}")

            res = result.stdout

        except subprocess.TimeoutExpired:
            all_tests_passed = False
            res = f"Test {test_file} timed out after {timeout} seconds."

        print(res)
        with history_fname.open("a") as fh:
            fh.write(f"```\n{res}\n```")

        if not all_tests_passed:
            return res


if __name__ == "__main__":
    main()
