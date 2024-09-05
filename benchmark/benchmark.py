#!/usr/bin/env python
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import time
import traceback
from collections import defaultdict
from json.decoder import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import List

import git
import lox
import pandas as pd
import prompts
import typer
from dotenv import load_dotenv
from plots import plot_refactoring
from rich.console import Console

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

BENCHMARK_DNAME = Path(os.environ.get("AIDER_BENCHMARK_DIR", "tmp.benchmarks"))

EXERCISES_DIR_DEFAULT = "exercism-python"

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


NUM_TESTS = (89, 133)

load_dotenv(override=True)


def show_stats(dirnames, graphs):
    raw_rows = []
    for dirname in dirnames:
        row = summarize_results(dirname)
        raw_rows.append(row)

    # return

    seen = dict()
    rows = []
    for row in raw_rows:
        if not row:
            continue

        if row.completed_tests not in NUM_TESTS:
            print(f"Warning: {row.dir_name} is incomplete: {row.completed_tests}")

        kind = (row.model, row.edit_format)
        if kind in seen:
            dump(row.dir_name)
            dump(seen[kind])
            return

        seen[kind] = row.dir_name
        rows.append(vars(row))

    repeat_hi = repeat_lo = repeat_avg = None  # noqa: F841

    df = pd.DataFrame.from_records(rows)
    # df.sort_values(by=["model", "edit_format"], inplace=True)

    # dump(df)
    if graphs:
        # plot_timing(df)
        # plot_outcomes(df, repeats, repeat_hi, repeat_lo, repeat_avg)
        # plot_outcomes_claude(df)
        plot_refactoring(df)


def resolve_dirname(dirname, use_single_prior, make_new):
    if len(dirname.parts) > 1:
        return dirname

    priors = list(BENCHMARK_DNAME.glob(f"*--{dirname}"))
    if len(priors) == 1 and use_single_prior:
        dirname = priors[0].name
        print(f"Using pre-existing {dirname}")
    elif len(priors):
        if not make_new:
            print(f"Prior runs of {dirname} exist, use --new or name one explicitly")
            print()
            for prior in priors:
                print(prior)
            return

    if not re.match(r"\d\d\d\d-\d\d-\d\d-", str(dirname)):
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S--")
        dirname = now + dirname.name

    dirname = BENCHMARK_DNAME / dirname
    return dirname


@app.command()
def main(
    dirnames: List[str] = typer.Argument(..., help="Directory names"),
    graphs: bool = typer.Option(False, "--graphs", help="Generate graphs"),
    model: str = typer.Option("gpt-3.5-turbo", "--model", "-m", help="Model name"),
    edit_format: str = typer.Option(None, "--edit-format", "-e", help="Edit format"),
    replay: str = typer.Option(
        None,
        "--replay",
        help="Replay previous .aider.chat.history.md responses from previous benchmark run",
    ),
    max_apply_update_errors: int = typer.Option(
        3,
        "--max-apply-update-errors",
        help="Maximum number of apply update errors before stopping the test",
    ),
    keywords: str = typer.Option(
        None, "--keywords", "-k", help="Only run tests that contain keywords (comma sep)"
    ),
    clean: bool = typer.Option(
        False, "--clean", "-c", help="Discard the existing testdir and make a clean copy"
    ),
    cont: bool = typer.Option(False, "--cont", help="Continue the (single) matching testdir"),
    make_new: bool = typer.Option(False, "--new", "-n", help="Make a new dated testdir"),
    no_unit_tests: bool = typer.Option(False, "--no-unit-tests", help="Do not run unit tests"),
    no_aider: bool = typer.Option(False, "--no-aider", help="Do not run aider"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    stats_only: bool = typer.Option(
        False, "--stats", "-s", help="Do not run tests, just collect stats on completed tests"
    ),
    diffs_only: bool = typer.Option(False, "--diffs", help="Just diff the provided stats dirs"),
    tries: int = typer.Option(2, "--tries", "-r", help="Number of tries for running tests"),
    threads: int = typer.Option(1, "--threads", "-t", help="Number of threads to run in parallel"),
    num_tests: int = typer.Option(-1, "--num-tests", "-n", help="Number of tests to run"),
    exercises_dir: str = typer.Option(
        EXERCISES_DIR_DEFAULT, "--exercises-dir", help="Directory with exercise files"
    ),
):
    repo = git.Repo(search_parent_directories=True)
    commit_hash = repo.head.object.hexsha[:7]
    if repo.is_dirty():
        commit_hash += "-dirty"

    if len(dirnames) > 1 and not (stats_only or diffs_only):
        print("Only provide 1 dirname unless running with --stats or --diffs")
        return 1

    updated_dirnames = []
    for dirname in dirnames:
        dirname = Path(dirname)
        dirname = resolve_dirname(dirname, stats_only or cont, make_new)
        if not dirname:
            return 1
        updated_dirnames.append(dirname)

    if stats_only:
        return show_stats(updated_dirnames, graphs)

    if diffs_only:
        return show_diffs(updated_dirnames)

    assert len(updated_dirnames) == 1, updated_dirnames
    dirname = updated_dirnames[0]

    if "AIDER_DOCKER" not in os.environ:
        print("Warning: benchmarking runs unvetted code from GPT, run in a docker container")
        return

    assert BENCHMARK_DNAME.exists() and BENCHMARK_DNAME.is_dir(), BENCHMARK_DNAME
    original_dname = BENCHMARK_DNAME / exercises_dir
    assert original_dname.exists() and original_dname.is_dir(), original_dname

    if clean and dirname.exists():
        print("Cleaning up and replacing", dirname)
        dir_files = set(fn.name for fn in dirname.glob("*"))
        original_files = set(fn.name for fn in original_dname.glob("*"))
        if dir_files != original_files:
            print("ERROR: will not delete dir that does not look like original tests", dirname)
            return

        dest = dirname.parent / "OLD" / dirname.name
        if dest.exists():
            old_now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            dest = dirname.parent / "OLD" / (old_now + dirname.name)

        dirname.rename(dest)

    if not dirname.exists():
        print(f"Copying {original_dname} -> {dirname} ...")
        shutil.copytree(original_dname, dirname)
        print("...done")

    test_dnames = sorted(os.listdir(dirname))

    if keywords:
        keywords = keywords.split(",")
        test_dnames = [dn for dn in test_dnames for keyword in keywords if keyword in dn]

    random.shuffle(test_dnames)
    if num_tests > 0:
        test_dnames = test_dnames[:num_tests]

    if threads == 1:
        all_results = []
        for testname in test_dnames:
            results = run_test(
                original_dname,
                dirname / testname,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
                replay,
                max_apply_update_errors,
            )

            all_results.append(results)
            summarize_results(dirname)
    else:
        run_test_threaded = lox.thread(threads)(run_test)
        for testname in test_dnames:
            run_test_threaded.scatter(
                original_dname,
                dirname / testname,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
                replay,
                max_apply_update_errors,
            )
        all_results = run_test_threaded.gather(tqdm=True)

    print()
    print()
    print()
    summarize_results(dirname)

    return 0


def show_diffs(dirnames):
    dirnames = sorted(dirnames)

    all_results = dict((dirname, load_results(dirname)) for dirname in dirnames)
    testcases = set()
    for results in all_results.values():
        testcases.update(result["testcase"] for result in results)

    testcases = sorted(testcases)

    unchanged = set()

    for testcase in testcases:
        all_outcomes = []
        for dirname in dirnames:
            results = all_results[dirname]
            result = [r for r in results if r["testcase"] == testcase][0]

            outcomes = tuple(result["tests_outcomes"])
            all_outcomes.append(True in outcomes)

        if len(set(all_outcomes)) == 1:
            unchanged.add(testcase)
            continue

        print()
        print(testcase)
        for outcome, dirname in zip(all_outcomes, dirnames):
            print(outcome, f"{dirname}/{testcase}/.aider.chat.history.md")

    changed = set(testcases) - unchanged
    print()
    print("changed:", len(changed), ",".join(sorted(changed)))
    print()
    print("unchanged:", len(unchanged), ",".join(sorted(unchanged)))


def load_results(dirname):
    dirname = Path(dirname)
    all_results = [json.loads(fname.read_text()) for fname in dirname.glob("*/.aider.results.json")]
    return all_results


def summarize_results(dirname):
    all_results = load_results(dirname)

    res = SimpleNamespace()
    res.total_tests = len(list(Path(dirname).glob("*")))

    try:
        tries = max(len(results.get("tests_outcomes", [])) for results in all_results if results)
    except ValueError:
        tries = 0

    res.dir_name = str(dirname)

    passed_tests = [0] * tries

    res.completed_tests = 0
    res.duration = 0
    res.cost = 0
    res.error_outputs = 0
    res.user_asks = 0
    res.test_timeouts = 0
    res.exhausted_context_windows = 0
    res.num_malformed_responses = 0
    res.num_with_malformed_responses = 0
    res.syntax_errors = 0
    res.indentation_errors = 0
    res.lazy_comments = 0

    variants = defaultdict(set)

    for results in all_results:
        if not results:
            continue

        res.completed_tests += 1
        tests_outcomes = results.get("tests_outcomes", [])
        passed = tests_outcomes and tests_outcomes[-1]
        if passed:
            for i in range(len(tests_outcomes) - 1, tries):
                passed_tests[i] += 1

        res.cost += results.get("cost", 0)
        res.duration += results.get("duration", 0)
        res.test_timeouts += results.get("test_timeouts", 0)

        res.error_outputs += results.get("num_error_outputs", 0)
        res.user_asks += results.get("num_user_asks", 0)
        res.exhausted_context_windows += results.get("num_exhausted_context_windows", 0)
        res.num_malformed_responses += results.get("num_malformed_responses", 0)
        if results.get("num_malformed_responses"):
            res.num_with_malformed_responses += 1
        res.lazy_comments += results.get("lazy_comments", 0)

        res.syntax_errors += results.get("syntax_errors", 0)
        res.indentation_errors += results.get("indentation_errors", 0)

        for key in "model edit_format commit_hash".split():
            val = results.get(key)
            if val:
                variants[key].add(val)

    if not res.completed_tests:
        return

    # if res.completed_tests < 133:
    #    return

    console = Console(highlight=False)
    console.rule(title=str(dirname))

    commit_hashes = variants["commit_hash"]
    versions = get_versions(commit_hashes)
    date = dirname.name[:10]

    def show(stat, red="red"):
        val = getattr(res, stat)
        style = red if val else None
        console.print(f"  {stat}: {val}", style=style)

    percents = dict()
    for i in range(tries):
        pass_rate = 100 * passed_tests[i] / res.completed_tests
        percents[i] = pass_rate
        # console.print(f"{pass_rate:.1f}% correct after try {i+1}")
        setattr(res, f"pass_rate_{i + 1}", f"{pass_rate:.1f}")

    print(f"- dirname: {dirname.name}")
    style = None if res.completed_tests in NUM_TESTS else "red"
    console.print(f"  test_cases: {res.completed_tests}", style=style)
    for key, val in variants.items():
        if len(val) > 1:
            style = "red"
        else:
            style = None
        val = ", ".join(map(str, val))
        setattr(res, key, val)
        console.print(f"  {key}: {val}", style=style)

    for i in range(tries):
        print(f"  pass_rate_{i + 1}: {percents[i]:.1f}")

    pct_well_formed = 1.0 - res.num_with_malformed_responses / res.completed_tests
    print(f"  percent_cases_well_formed: {pct_well_formed * 100:.1f}")

    show("error_outputs")
    show("num_malformed_responses")
    show("num_with_malformed_responses")
    show("user_asks")
    show("lazy_comments")
    show("syntax_errors")
    show("indentation_errors")
    show("exhausted_context_windows")
    show("test_timeouts")

    a_model = set(variants["model"]).pop()
    command = f"aider --model {a_model}"
    print(f"  command: {command}")

    print(f"  date: {date}")
    print("  versions:", ",".join(versions))

    res.avg_duration = res.duration / res.completed_tests
    print(f"  seconds_per_case: {res.avg_duration:.1f}")

    print(f"  total_cost: {res.cost:.4f}")

    res.avg_cost = res.cost / res.completed_tests

    projected_cost = res.avg_cost * res.total_tests

    print()
    print(
        f"costs: ${res.avg_cost:.4f}/test-case, ${res.cost:.2f} total,"
        f" ${projected_cost:.2f} projected"
    )

    console.rule()

    # print(json.dumps(vars(res), indent=4, sort_keys=True))
    return res


def get_versions(commit_hashes):
    versions = set()
    for hsh in commit_hashes:
        if not hsh:
            continue
        hsh = hsh.split("-")[0]
        try:
            version = subprocess.check_output(
                ["git", "show", f"{hsh}:aider/__init__.py"], universal_newlines=True
            )
            version = re.search(r'__version__ = "(.*)"', version).group(1)
            versions.add(version)
        except subprocess.CalledProcessError:
            pass
    return versions


def get_replayed_content(replay_dname, test_dname):
    replay_dname = Path(replay_dname)
    test_dname = Path(test_dname)
    dump(replay_dname, test_dname)

    test_name = test_dname.name
    replay_fname = replay_dname / test_name / ".aider.chat.history.md"
    dump(replay_fname)

    res = replay_fname.read_text()
    return res

    res = res.splitlines(keepends=True)
    res = [line for line in res if not line.startswith("> ") and not line.startswith("#### ")]
    return "".join(res)


def run_test(original_dname, testdir, *args, **kwargs):
    try:
        return run_test_real(original_dname, testdir, *args, **kwargs)
    except Exception as err:
        print("=" * 40)
        print("Test failed")
        print(err)
        traceback.print_exc()

        testdir = Path(testdir)
        results_fname = testdir / ".aider.results.json"
        results_fname.write_text(json.dumps(dict(exception=str(err))))


def run_test_real(
    original_dname,
    testdir,
    model_name,
    edit_format,
    tries,
    no_unit_tests,
    no_aider,
    verbose,
    commit_hash,
    replay,
    max_apply_update_errors,
):
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

    fnames = []
    for fname in testdir.glob("*"):
        if (
            "test" not in fname.name
            and fname.is_file()
            and fname.name[0] != "."
            and fname.suffix == ".py"
        ):
            fnames.append(fname)

            # restore the original file, in case we interrupted a prev run
            # after it had saved changes
            original_fname = original_dname / testdir.name / fname.name
            shutil.copy(original_fname, fname)

    file_list = " ".join(fname.name for fname in fnames)

    instructions = ""

    introduction = testdir / ".docs/introduction.md"
    if introduction.exists():
        instructions += introduction.read_text()
    instructions += (testdir / ".docs/instructions.md").read_text()
    instructions_append = testdir / ".docs/instructions.append.md"
    if instructions_append.exists():
        instructions += instructions_append.read_text()

    instructions += prompts.instructions_addendum.format(file_list=file_list)

    io = InputOutput(
        pretty=True,
        yes=False,
        chat_history_file=history_fname,
    )

    main_model = models.Model(model_name)
    edit_format = edit_format or main_model.edit_format

    dump(main_model)
    dump(edit_format)
    show_fnames = ",".join(map(str, fnames))
    print("fnames:", show_fnames)

    coder = Coder.create(
        main_model,
        edit_format,
        io,
        fnames=fnames,
        use_git=False,
        stream=False,
        verbose=verbose,
        # auto_lint=False,  # disabled for code-in-json experiments
        cache_prompts=True,
        suggest_shell_commands=False,
    )
    coder.max_apply_update_errors = max_apply_update_errors

    timeouts = 0

    syntax_errors = 0
    indentation_errors = 0
    lazy_comments = 0

    dur = 0
    test_outcomes = []
    for i in range(tries):
        start = time.time()
        if no_aider:
            pass
        elif replay:
            response = get_replayed_content(replay, testdir)
            coder.partial_response_content = response

            show = response.splitlines(keepends=True)
            show = [">> " + line for line in show]
            io.append_chat_history("".join(show))

            coder.apply_updates()
        else:
            response = coder.run(with_message=instructions, preproc=False)
        dur += time.time() - start

        if not no_aider:
            pat = r"^[+]? *[#].* [.][.][.] "
            # Count the number of lines that match pat in response
            dump(response)
            lazy_comments += len(re.findall(pat, response, re.MULTILINE))
            dump(lazy_comments)

        if coder.last_keyboard_interrupt:
            raise KeyboardInterrupt

        if no_unit_tests:
            break

        try:
            errors = run_unit_tests(testdir, history_fname)
        except subprocess.TimeoutExpired:
            errors = "Tests timed out!"
            timeouts += 1

        if errors:
            test_outcomes.append(False)
        else:
            test_outcomes.append(True)
            break

        if replay:
            io.append_chat_history(errors)

        errors = errors.splitlines()

        syntax_errors += sum(1 for line in errors if line.startswith("SyntaxError"))
        indentation_errors += sum(1 for line in errors if line.startswith("IndentationError"))

        print(errors[-1])
        errors = errors[:50]
        errors = "\n".join(errors)
        instructions = errors
        instructions += prompts.test_failures.format(file_list=file_list)

    results = dict(
        testdir=str(testdir),
        testcase=testdir.name,
        model=main_model.name,
        edit_format=edit_format,
        tests_outcomes=test_outcomes,
        cost=coder.total_cost,
        duration=dur,
        test_timeouts=timeouts,
        commit_hash=commit_hash,
        num_error_outputs=io.num_error_outputs,
        num_user_asks=io.num_user_asks,
        num_exhausted_context_windows=coder.num_exhausted_context_windows,
        num_malformed_responses=coder.num_malformed_responses,
        syntax_errors=syntax_errors,
        indentation_errors=indentation_errors,
        lazy_comments=lazy_comments,  # Add the count of pattern matches to the results
        chat_hashes=list(
            zip(
                coder.chat_completion_call_hashes,
                coder.chat_completion_response_hashes,
            )
        ),
    )
    dump(results)

    results_fname.write_text(json.dumps(results, indent=4))

    return results


def run_unit_tests(testdir, history_fname):
    command = [
        "python",
        "-m",
        "unittest",
        "discover",
        "-s",
        str(testdir),
        "-t",
        str(testdir),
        "-p",
        "*_test.py",
    ]
    print(" ".join(command))

    timeout = 60

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )

    success = result.returncode == 0
    res = result.stdout
    res = cleanup_test_output(res, testdir)

    with history_fname.open("a") as fh:
        fh.write(f"```\n{res}\n```")

    if not success:
        print(f"Tests failed: {testdir}")
        return res


def cleanup_test_output(output, testdir):
    # remove timing info, to avoid randomizing the response to GPT
    res = re.sub(
        r"^Ran \d+ tests in \d+\.\d+s$",
        "",
        output,
        flags=re.MULTILINE,
    )
    res = re.sub(
        r"^====*$",
        "====",
        res,
        flags=re.MULTILINE,
    )
    res = re.sub(
        r"^----*$",
        "----",
        res,
        flags=re.MULTILINE,
    )

    res = res.replace(str(testdir), str(testdir.name))
    return res


if __name__ == "__main__":
    app()
