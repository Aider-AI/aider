import argparse
import datetime
import json
import os
import random
import shutil
import subprocess
import time
from json.decoder import JSONDecodeError
from pathlib import Path

import lox
from rich.console import Console

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

ORIGINAL_DNAME = Path("tmp.benchmark/practice")
assert ORIGINAL_DNAME.exists()


console = Console(style="green", highlight=False)


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
        "--no-test",
        action="store_true",
        help="Do not run tests",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--stats-only",
        "-s",
        action="store_true",
        help="Do not run tests, just collect stats on completed tests",
    )
    parser.add_argument(
        "--retries",
        "-r",
        type=int,
        help="Number of retries for running tests",
        default=2,
    )
    parser.add_argument(
        "--threads",
        "-t",
        type=int,
        help="Number of threads to run in parallel",
        default=1,
    )
    parser.add_argument(
        "--num-tests",
        "-n",
        type=int,
        help="Number of tests to run",
        default=-1,
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

    test_dnames = sorted(os.listdir(dirname))
    total_tests = len(test_dnames)

    if args.keyword:
        test_dnames = [dn for dn in test_dnames if args.keyword in dn]

    random.shuffle(test_dnames)
    if args.num_tests > 0:
        test_dnames = test_dnames[: args.num_tests]

    if args.threads == 1:
        all_results = []
        for testname in test_dnames:
            results = run_test(
                dirname / testname,
                args.model,
                args.edit_format,
                args.retries,
                args.no_test,
                args.verbose,
                args.stats_only,
            )

            all_results.append(results)
            if not args.stats_only:
                summarize_results(all_results, total_tests)
    else:
        run_test_threaded = lox.thread(args.threads)(run_test)
        for testname in test_dnames:
            run_test_threaded.scatter(
                dirname / testname,
                args.model,
                args.edit_format,
                args.retries,
                args.no_test,
                args.verbose,
            )
        all_results = run_test_threaded.gather(tqdm=True)

    if not args.stats_only:
        print()
        print()
        print()
    summarize_results(all_results, total_tests)


def summarize_results(all_results, total_tests=None):
    if not total_tests:
        total_tests = len(all_results)

    completed_tests = 0
    retries = max(len(results["tests_outcomes"]) for results in all_results if results)

    passed_tests = [0] * retries
    duration = 0
    total_cost = 0

    for results in all_results:
        if not results:
            continue

        completed_tests += 1
        passed = results["tests_outcomes"][-1]
        if passed:
            for i in range(len(results["tests_outcomes"]) - 1, retries):
                passed_tests[i] += 1

        total_cost += results["cost"]
        duration += results["duration"]

    console.rule()

    console.print(f"{completed_tests} test-cases")
    for i in range(retries):
        pass_rate = 100 * passed_tests[i] / completed_tests
        console.print(f"{pass_rate:.1f}% correct after try {i}")

    avg_duration = duration / completed_tests
    console.print(f"{avg_duration:.1f} sec/test-case")

    avg_cost = total_cost / completed_tests

    projected_cost = avg_cost * total_tests

    console.print(
        f"Cost: ${avg_cost:.4f} average, ${total_cost:.2f} total, ${projected_cost:.2f} projected"
    )

    console.rule()


def run_test(testdir, model_name, edit_format, retries, no_test, verbose, stats_only):
    if not stats_only:
        dump(testdir)

    if not os.path.isdir(testdir):
        print("Not a dir:", testdir)
        return

    testdir = Path(testdir)

    history_fname = testdir / ".aider.chat.history.md"

    results_fname = testdir / ".aider.results.json"
    if results_fname.exists():
        try:
            res = json.loads(results_fname.read_text())
            return res
        except JSONDecodeError:
            print(f"{results_fname} failed to parse, skipping")
            return

    if stats_only:
        return

    fnames = []
    for fname in testdir.glob("*"):
        if "test" not in fname.name and fname.is_file() and fname.name[0] != ".":
            fnames.append(fname)

            # restore the original file, in case we interrupted a prev run
            # after it had saved changes
            original_fname = ORIGINAL_DNAME / testdir.name / fname.name
            shutil.copy(original_fname, fname)

    file_list = " ".join(fname.name for fname in fnames)
    instructions = (testdir / ".docs/instructions.md").read_text()
    instructions += (
        "\n\n=====\n\nModify these files according to the above instructions. Only use standard"
        " python libraries, don't suggest installing any packages.\n"
    )
    instructions += file_list

    io = InputOutput(
        pretty=True,
        yes=False,
        chat_history_file=history_fname,
    )

    main_model = models.Model(model_name)
    edit_format = edit_format or main_model.edit_format

    dump(main_model)
    dump(edit_format)
    dump(fnames)

    coder = Coder.create(
        main_model,
        edit_format,
        io,
        os.environ["OPENAI_API_KEY"],
        fnames=fnames,
        use_git=False,
        stream=False,
        pretty=False,
        verbose=verbose,
    )

    dur = 0
    test_outcomes = []
    for i in range(retries):
        start = time.time()
        coder.run(with_message=instructions)
        dur += time.time() - start

        if coder.num_control_c:
            raise KeyboardInterrupt

        if no_test:
            return

        errors = run_pytests(testdir, history_fname)

        if errors:
            test_outcomes.append(False)
        else:
            test_outcomes.append(True)
            break

        errors = errors.splitlines()
        print(errors[-1])
        errors = errors[:50]
        errors = "\n".join(errors)
        instructions = errors
        instructions += (
            "\n\n####\n\nFix the code in {file_list} to resolve the test failures above."
        )

    results = dict(
        testdir=str(testdir),
        testcase=testdir.name,
        model=main_model.name,
        edit_format=edit_format,
        tests_outcomes=test_outcomes,
        cost=coder.total_cost,
        duration=dur,
    )
    dump(results)

    results_fname.write_text(json.dumps(results, indent=4))

    return results


def run_pytests(testdir, history_fname):
    test_files = [file for file in testdir.glob("*") if file.name.endswith("_test.py")]
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
                print(f"Test {test_file} failed")

            res = result.stdout

        except subprocess.TimeoutExpired:
            all_tests_passed = False
            res = f"Test {test_file} timed out after {timeout} seconds."

        with history_fname.open("a") as fh:
            fh.write(f"```\n{res}\n```")

        if not all_tests_passed:
            return res


if __name__ == "__main__":
    main()
