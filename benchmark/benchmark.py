#!/usr/bin/env python

import datetime
import json
import os
import random
import re
import shutil
import subprocess
import time
from collections import defaultdict
from json.decoder import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import List

import git
import lox
import matplotlib.pyplot as plt
import numpy as np
import openai
import pandas as pd
import prompts
import typer
from imgcat import imgcat
from rich.console import Console

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

BENCHMARK_DNAME = Path(os.environ["AIDER_BENCHMARK_DIR"])

ORIGINAL_DNAME = BENCHMARK_DNAME / "exercism-python"

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


def show_stats(dirnames):
    raw_rows = []
    for dirname in dirnames:
        row = summarize_results(dirname)
        raw_rows.append(row)

    return

    repeats = []
    seen = dict()
    rows = []
    for row in raw_rows:
        if not row:
            continue

        if row.model == "gpt-3.5-turbo":
            row.model = "gpt-3.5-turbo-0613"
        if row.edit_format == "diff-func-string":
            row.edit_format = "diff-func"

        if (
            row.model == "gpt-3.5-turbo-0613"
            and row.edit_format == "whole"
            and "repeat" not in row.dir_name
        ):
            # remember this row, so we can update it with the repeat_avg
            repeat_row = len(rows)

        pieces = row.model.split("-")
        row.model = "-".join(pieces[:3])
        if pieces[3:]:
            row.model += "\n-" + "-".join(pieces[3:])

        if row.completed_tests < 133:
            print(f"Warning: {row.dir_name} is incomplete: {row.completed_tests}")

        if "repeat" in row.dir_name:
            repeats.append(vars(row))
            continue

        kind = (row.model, row.edit_format)
        if kind in seen:
            dump(row.dir_name)
            dump(seen[kind])
            return

        seen[kind] = row.dir_name
        rows.append(vars(row))

    if repeats:
        extra = rows[repeat_row]
        dump(extra)
        repeats.append(extra)
        repeats = pd.DataFrame.from_records(repeats)
        repeat_max = repeats["pass_rate_2"].max()
        repeat_min = repeats["pass_rate_2"].min()
        repeat_avg = repeats["pass_rate_2"].mean()

        repeat_lo = repeat_avg - repeat_min
        repeat_hi = repeat_max - repeat_avg

        dump(repeat_max)
        dump(repeat_min)
        dump(repeat_avg)

        # use the average in the main bar
        rows[repeat_row]["pass_rate_2"] = repeat_avg

    df = pd.DataFrame.from_records(rows)
    df.sort_values(by=["model", "edit_format"], inplace=True)

    tries = [df.groupby(["model", "edit_format"])["pass_rate_2"].mean()]
    if True:
        tries += [df.groupby(["model", "edit_format"])["pass_rate_1"].mean()]

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    for grouped in tries:
        zorder += 1
        df = grouped.unstack()
        num_models, num_formats = df.shape

        pos = np.array(range(num_models))
        width = 0.8 / num_formats

        formats = df.columns
        models = df.index

        for i, fmt in enumerate(formats):
            if zorder > 1:
                edge = dict(
                    edgecolor="#ffffff",
                    linewidth=1.5,
                )
            else:
                edge = dict()
            if zorder == 2:
                edge["label"] = fmt

            color = "#b3e6a8" if "diff" in fmt else "#b3d1e6"
            hatch = "////" if "func" in fmt else ""
            rects = ax.bar(
                pos + i * width,
                df[fmt],
                width * 0.95,
                color=color,
                hatch=hatch,
                zorder=zorder,
                **edge,
            )
            if zorder == 2:
                ax.bar_label(rects, padding=4, labels=[f"{v:.0f}%" for v in df[fmt]], size=6)

    if len(repeats):
        ax.errorbar(
            1.4,
            repeat_avg,
            yerr=[[repeat_lo], [repeat_hi]],
            fmt="none",
            zorder=5,
            capsize=2.5,
            elinewidth=1,
            markeredgewidth=1,
        )

    ax.set_xticks([p + 1.5 * width for p in pos])
    ax.set_xticklabels(models)

    top = 95
    ax.annotate(
        "First attempt,\nbased on\ninstructions",
        xy=(2.9, 51),
        xytext=(2.5, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )
    ax.annotate(
        "Second attempt,\nbased on\nunit test errors",
        xy=(3.1, 68),
        xytext=(4.25, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title("GPT Code Editing")
    ax.legend(
        title="Edit Format",
        loc="upper left",
        # bbox_to_anchor=(0.95, 0.95),
    )
    ax.set_ylim(top=100)

    plt.tight_layout()
    plt.savefig("tmp.svg")
    imgcat(fig)

    # df.to_csv("tmp.benchmarks.csv")


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
    model: str = typer.Option("gpt-3.5-turbo", "--model", "-m", help="Model name"),
    edit_format: str = typer.Option(None, "--edit-format", "-e", help="Edit format"),
    keyword: str = typer.Option(
        None, "--keyword", "-k", help="Only run tests that contain keyword"
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
    tries: int = typer.Option(2, "--tries", "-r", help="Number of tries for running tests"),
    threads: int = typer.Option(1, "--threads", "-t", help="Number of threads to run in parallel"),
    num_tests: int = typer.Option(-1, "--num-tests", "-n", help="Number of tests to run"),
):
    repo = git.Repo(search_parent_directories=True)
    commit_hash = repo.head.object.hexsha[:7]
    if repo.is_dirty():
        commit_hash += "-dirty"

    if len(dirnames) > 1 and not stats_only:
        print("Only provide 1 dirname unless running with --stats")
        return 1

    updated_dirnames = []
    for dirname in dirnames:
        dirname = Path(dirname)
        dirname = resolve_dirname(dirname, stats_only or cont, make_new)
        if not dirname:
            return 1
        updated_dirnames.append(dirname)

    if stats_only:
        return show_stats(updated_dirnames)

    assert len(updated_dirnames) == 1, updated_dirnames
    dirname = updated_dirnames[0]

    if "AIDER_DOCKER" not in os.environ:
        print("Warning: benchmarking runs unvetted code from GPT, run in a docker container")
        return

    assert BENCHMARK_DNAME.exists() and BENCHMARK_DNAME.is_dir(), BENCHMARK_DNAME
    assert ORIGINAL_DNAME.exists() and ORIGINAL_DNAME.is_dir(), ORIGINAL_DNAME

    if clean and dirname.exists():
        print("Cleaning up and replacing", dirname)
        dir_files = set(fn.name for fn in dirname.glob("*"))
        original_files = set(fn.name for fn in ORIGINAL_DNAME.glob("*"))
        if dir_files != original_files:
            print("ERROR: will not delete dir that does not look like original tests", dirname)
            return

        dest = dirname.parent / "OLD" / dirname.name
        if dest.exists():
            old_now = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            dest = dirname.parent / "OLD" / (old_now + dirname.name)

        dirname.rename(dest)

    if not dirname.exists():
        shutil.copytree(ORIGINAL_DNAME, dirname)

    test_dnames = sorted(os.listdir(dirname))

    if keyword:
        test_dnames = [dn for dn in test_dnames if keyword in dn]

    random.shuffle(test_dnames)
    if num_tests > 0:
        test_dnames = test_dnames[:num_tests]

    if threads == 1:
        all_results = []
        for testname in test_dnames:
            results = run_test(
                dirname / testname,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
            )

            all_results.append(results)
            summarize_results(dirname)
    else:
        run_test_threaded = lox.thread(threads)(run_test)
        for testname in test_dnames:
            run_test_threaded.scatter(
                dirname / testname,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
            )
        all_results = run_test_threaded.gather(tqdm=True)

    print()
    print()
    print()
    summarize_results(dirname)

    return 0


def summarize_results(dirname):
    res = SimpleNamespace()
    dirname = Path(dirname)
    res.total_tests = len(list(dirname.glob("*")))
    all_results = [json.loads(fname.read_text()) for fname in dirname.glob("*/.aider.results.json")]

    try:
        tries = max(len(results["tests_outcomes"]) for results in all_results if results)
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

    variants = defaultdict(set)

    for results in all_results:
        if not results:
            continue

        res.completed_tests += 1
        passed = results["tests_outcomes"][-1]
        if passed:
            for i in range(len(results["tests_outcomes"]) - 1, tries):
                passed_tests[i] += 1

        res.cost += results["cost"]
        res.duration += results["duration"]
        res.test_timeouts += results.get("test_timeouts", 0)

        res.error_outputs += results.get("num_error_outputs", 0)
        res.user_asks += results.get("num_user_asks", 0)
        res.exhausted_context_windows += results.get("num_exhausted_context_windows", 0)

        for key in "model edit_format commit_hash".split():
            val = results.get(key)
            variants[key].add(val)

    if not res.completed_tests:
        return

    console = Console(highlight=False)
    console.rule(title=str(dirname))

    console.print(f"test-cases: {res.completed_tests}")
    for key, val in variants.items():
        if len(val) > 1:
            style = "red"
        else:
            style = None
        val = ", ".join(map(str, val))
        setattr(res, key, val)
        console.print(f"{key}: {val}", style=style)
    print("num_error_outputs:", res.error_outputs)
    print("num_user_asks:", res.user_asks)

    style = "red" if res.exhausted_context_windows else None
    console.print("num_exhausted_context_windows", res.exhausted_context_windows, style=style)

    style = "red" if res.test_timeouts else None
    console.print("test_timeouts:", res.test_timeouts, style=style)

    console.print()
    for i in range(tries):
        pass_rate = 100 * passed_tests[i] / res.completed_tests
        console.print(f"{pass_rate:.1f}% correct after try {i}")
        setattr(res, f"pass_rate_{i+1}", pass_rate)

    console.print()
    res.avg_duration = res.duration / res.completed_tests

    console.print(f"duration: {res.avg_duration:.1f} sec/test-case")

    res.avg_cost = res.cost / res.completed_tests

    projected_cost = res.avg_cost * res.total_tests

    console.print(
        f"costs: ${res.avg_cost:.4f}/test-case, ${res.cost:.2f} total,"
        f" ${projected_cost:.2f} projected"
    )

    console.rule()

    # print(json.dumps(vars(res), indent=4, sort_keys=True))
    return res


def run_test(
    testdir, model_name, edit_format, tries, no_unit_tests, no_aider, verbose, commit_hash
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
        if "test" not in fname.name and fname.is_file() and fname.name[0] != ".":
            fnames.append(fname)

            # restore the original file, in case we interrupted a prev run
            # after it had saved changes
            original_fname = ORIGINAL_DNAME / testdir.name / fname.name
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

    openai.api_key = os.environ["OPENAI_API_KEY"]

    coder = Coder.create(
        main_model,
        edit_format,
        io,
        fnames=fnames,
        use_git=False,
        stream=False,
        pretty=False,
        verbose=verbose,
    )

    timeouts = 0

    dur = 0
    test_outcomes = []
    for i in range(tries):
        start = time.time()
        if not no_aider:
            coder.run(with_message=instructions)
        dur += time.time() - start

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

        errors = errors.splitlines()
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
    res = cleanup_test_output(res)

    with history_fname.open("a") as fh:
        fh.write(f"```\n{res}\n```")

    if not success:
        print(f"Tests failed: {testdir}")
        return res


def cleanup_test_output(output):
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
    return res


if __name__ == "__main__":
    app()
