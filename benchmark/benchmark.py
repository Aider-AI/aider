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

BENCHMARK_DNAME = Path(os.environ.get("AIDER_BENCHMARK_DIR", "tmp.benchmarks"))

EXERCISES_DIR_DEFAULT = "exercism-python"

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


def show_stats(dirnames, graphs):
    raw_rows = []
    for dirname in dirnames:
        row = summarize_results(dirname)
        raw_rows.append(row)

    # return

    repeats = []
    seen = dict()
    rows = []
    for row in raw_rows:
        if not row:
            continue

        if row.model == "gpt-3.5-turbo":
            row.model = "gpt-3.5-turbo-0613"

        if row.model == "gpt-4":
            row.model = "gpt-4-0613"

        if row.edit_format == "diff-func-string":
            row.edit_format = "diff-func"

        if (
            row.model == "gpt-3.5-turbo-0613"
            and row.edit_format == "whole"
            and "repeat" not in row.dir_name
        ):
            # remember this row, so we can update it with the repeat_avg
            repeat_row = len(rows)

        # gpt35 = "gpt-3.5-turbo"
        # gpt4 = "gpt-4"
        # if row.model.startswith(gpt35):
        #    row.model = gpt35 + "\n" + row.model[len(gpt35) :]
        # elif row.model.startswith(gpt4):
        #    row.model = gpt4 + "\n" + row.model[len(gpt4) :]

        if "folk" in row.dir_name:
            row.edit_format += "folk"

        # if row.model == "gpt-4-0613":
        #    row.model += "\n(8k context window is\ntoo small for benchmark)"

        if row.completed_tests < 89:
            print(f"Warning: {row.dir_name} is incomplete: {row.completed_tests}")

        # if "repeat" in row.dir_name:
        #    repeats.append(vars(row))
        #    continue

        kind = (row.model, row.edit_format)
        if kind in seen:
            dump(row.dir_name)
            dump(seen[kind])
            return

        seen[kind] = row.dir_name
        rows.append(vars(row))

    if repeats:
        dump(repeats)
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
    else:
        repeat_hi = repeat_lo = repeat_avg = None  # noqa: F841

    df = pd.DataFrame.from_records(rows)
    # df.sort_values(by=["model", "edit_format"], inplace=True)

    # dump(df)
    if graphs:
        # plot_timing(df)
        # plot_outcomes(df, repeats, repeat_hi, repeat_lo, repeat_avg)
        plot_outcomes_claude(df)
        # plot_refactoring(df)


def plot_timing(df):
    """plot a graph showing the average duration of each (model, edit_format)"""
    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    grouped = df.groupby(["model", "edit_format"])["avg_duration"].mean().unstack()
    num_models, num_formats = grouped.shape

    pos = np.array(range(num_models))
    width = 0.8 / num_formats

    formats = grouped.columns
    models = grouped.index

    for i, fmt in enumerate(formats):
        edge = dict(edgecolor="#ffffff", linewidth=1.5)
        color = "#b3e6a8" if "diff" in fmt else "#b3d1e6"
        hatch = "////" if "func" in fmt else ""
        rects = ax.bar(
            pos + i * width,
            grouped[fmt],
            width * 0.95,
            label=fmt,
            color=color,
            hatch=hatch,
            zorder=zorder + 1,
            **edge,
        )
        ax.bar_label(rects, padding=4, labels=[f"{v:.1f}s" for v in grouped[fmt]], size=6)

    ax.set_xticks([p + 0.5 * width for p in pos])
    ax.set_xticklabels(models)

    ax.set_ylabel("Average GPT response time\nper exercise (sec)")
    ax.set_title("GPT Code Editing Speed\n(time per coding task)")
    ax.legend(
        title="Edit Format",
        loc="upper left",
    )
    ax.set_ylim(top=max(grouped.max()) * 1.1)  # Set y-axis limit to 10% more than the max value

    plt.tight_layout()
    plt.savefig("tmp_timing.svg")
    imgcat(fig)


def plot_outcomes(df, repeats, repeat_hi, repeat_lo, repeat_avg):
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

    ax.set_xticks([p + 0.5 * width for p in pos])
    model_labels = []
    for model in models:
        pieces = model.split("-")
        ml = "-".join(pieces[:2]) + "-\n" + "-".join(pieces[2:])
        model_labels.append(ml)

    ax.set_xticklabels(model_labels)

    top = 95
    ax.annotate(
        "First attempt,\nbased on\nnatural language\ninstructions",
        xy=(2.20, 41),
        xytext=(2, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )
    ax.annotate(
        "Second attempt,\nincluding unit test\nerror output",
        xy=(2.55, 56),
        xytext=(3.5, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title("GPT Code Editing Skill\n(percent coding tasks correct)")
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


def plot_outcomes_claude(df):
    print(df)

    # Fix wrong column label
    df["model"] = df["model"].replace("gpt-4-0314", "gpt-4-0613")

    tries = [
        df[["model", "pass_rate_2"]],
        df[["model", "pass_rate_1"]],
    ]

    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    from matplotlib import rc

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)

    zorder = 1
    for df in tries:
        zorder += 1
        print(df)

        num_models, _ = df.shape
        num_formats = 1

        pos = np.array(range(num_models))
        width = 0.6 / num_formats

        if zorder > 1:
            edge = dict(
                edgecolor="#ffffff",
                linewidth=1.5,
            )
        else:
            edge = dict()
        if zorder == 2:
            edge["label"] = "??"

        color = [
            "#b3e6a8",
            "#b3e6a8",
            "#b3e6a8",
            "#b3e6a8",
            "#b3d1e6",
            "#b3d1e6",
            "#b3d1e6",
            "#e6b3b3",
            "#d1b3e6",
        ]
        hatch = [
            "",
            "",
            "",
            "",
            "////",
            "////",
            "////",
            "",
            "////",
        ]
        hatch = [
            "////",
            "////",
            "////",
            "////",
            "",
            "",
            "",
            "////",
            "",
        ]
        rects = ax.bar(
            pos + 0.5 * width,
            df.iloc[:, 1],
            width * 0.95,
            color=color,
            hatch=hatch,
            zorder=zorder,
            **edge,
        )
        if zorder == 2:
            ax.bar_label(rects, padding=4, labels=[f"{v:.0f}%" for v in df.iloc[:, 1]], size=6)

    ax.set_xticks([p + 0.5 * width for p in pos])
    model_labels = []
    for model in df.iloc[:, 0]:
        pieces = model.split("-")
        N = 3
        ml = "-".join(pieces[:N])
        if pieces[N:]:
            ml += "-\n" + "-".join(pieces[N:])
        model_labels.append(ml)

    ax.set_xticklabels(model_labels, rotation=60)

    top = 95
    ax.annotate(
        "First attempt,\nbased on\nnatural language\ninstructions",
        xy=(2.0, 41),
        xytext=(1.75, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )
    ax.annotate(
        "Second attempt,\nincluding unit test\nerror output",
        xy=(2.55, 56),
        xytext=(3.9, top),
        horizontalalignment="center",
        verticalalignment="top",
        arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=0.3"},
    )

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title("Code Editing Skill")
    # ax.legend(
    #    title="Model family",
    #    loc="upper left",
    # )
    ax.set_ylim(top=100)

    plt.tight_layout()
    plt.savefig("tmp.svg")
    imgcat(fig)

    # df.to_csv("tmp.benchmarks.csv")


def plot_refactoring(df):
    tries = [df.groupby(["model", "edit_format"])["pass_rate_1"].mean()]

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
        df.sort_values(by=["model"], ascending=False, inplace=True)
        num_models, num_formats = df.shape

        pos = np.array(range(num_models))
        width = 0.8 / num_formats

        formats = df.columns
        models = df.index

        dump(df)
        dump(models)
        dump(formats)
        for i, fmt in enumerate(formats):
            hatch = ""

            if fmt == "diff":
                color = "#b3e6a8"
                label = "Search/replace blocks"
            elif fmt == "udiff":
                color = "#b3d1e6"
                label = "Unified diffs"
            elif fmt == "difffolk":
                label = "Baseline + blind, no hands, $2k tip, etc"
                color = "#b3e6a8"
                hatch = "////"
            elif fmt == "udifffolk":
                label = "Unified diffs + blind, no hands, $2k tip, etc"
                color = "#b3d1e6"
                hatch = "////"

            if zorder > 1:
                edge = dict(
                    edgecolor="#ffffff",
                    linewidth=1.5,
                )
            else:
                edge = dict()
            if zorder == 2:
                edge["label"] = label

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

    ax.set_xticks([p + 0.5 * width for p in pos])
    ax.set_xticklabels(models)

    ax.set_ylabel("Percent of exercises completed successfully")
    # ax.set_xlabel("Model")
    ax.set_title('Refactoring "Laziness" Benchmark\n(percent coding tasks correct)')
    ax.legend(
        # title="Edit Format",
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
    res.num_malformed_responses = 0
    res.syntax_errors = 0
    res.indentation_errors = 0
    res.lazy_comments = 0

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
        res.num_malformed_responses += results.get("num_malformed_responses", 0)
        res.lazy_comments += results.get("lazy_comments", 0)

        res.syntax_errors += results.get("syntax_errors", 0)
        res.indentation_errors += results.get("indentation_errors", 0)

        for key in "model edit_format commit_hash".split():
            val = results.get(key)
            variants[key].add(val)

    if not res.completed_tests:
        return

    # if res.completed_tests < 133:
    #    return

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

    def show(stat):
        val = getattr(res, stat)
        style = "red" if val else None
        console.print(f"{stat}: {val}", style=style)

    console.print()
    show("error_outputs")
    show("user_asks")
    show("lazy_comments")
    show("num_malformed_responses")
    show("syntax_errors")
    show("indentation_errors")
    console.print()
    show("exhausted_context_windows")
    show("test_timeouts")

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


def run_test(
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

    if "OPENAI_API_BASE" in os.environ and "openrouter.ai" in os.environ["OPENAI_API_BASE"]:
        client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_API_BASE"),
            default_headers={
                "HTTP-Referer": "http://aider.chat",
                "X-Title": "Aider",
            },
        )
    else:
        client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
        )

    main_model = models.Model.create(model_name, client)
    edit_format = edit_format or main_model.edit_format

    dump(main_model)
    dump(edit_format)
    show_fnames = ",".join(map(str, fnames))
    print("fnames:", show_fnames)

    coder = Coder.create(
        main_model,
        edit_format,
        io,
        client=client,
        fnames=fnames,
        use_git=False,
        stream=False,
        pretty=False,
        verbose=verbose,
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
            response = coder.run(with_message=instructions)
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
