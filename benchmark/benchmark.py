#!/usr/bin/env python3
import datetime
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from json.decoder import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

import git
import importlib_resources
import lox
import pandas as pd
import prompts
import typer
from dotenv import load_dotenv
from plots import plot_refactoring
from rich.console import Console

from aider import models, sendchat
from aider.coders import Coder, base_coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput

BENCHMARK_DNAME = Path(os.environ.get("AIDER_BENCHMARK_DIR", "tmp.benchmarks"))

EXERCISES_DIR_DEFAULT = "polyglot-benchmark"

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


load_dotenv(override=True)


def find_latest_benchmark_dir():
    benchmark_dirs = [d for d in BENCHMARK_DNAME.iterdir() if d.is_dir()]
    if not benchmark_dirs:
        print("Error: No benchmark directories found under tmp.benchmarks.")
        sys.exit(1)

    # Get current time and 24 hours ago
    now = datetime.datetime.now()
    day_ago = now - datetime.timedelta(days=1)

    # Filter directories by name pattern YYYY-MM-DD-HH-MM-SS--
    recent_dirs = []
    for d in benchmark_dirs:
        try:
            # Extract datetime from directory name
            date_str = d.name[:19]  # Takes YYYY-MM-DD-HH-MM-SS
            dir_date = datetime.datetime.strptime(date_str, "%Y-%m-%d-%H-%M-%S")
            if dir_date >= day_ago:
                recent_dirs.append(d)
        except ValueError:
            # Skip directories that don't match the expected format
            continue

    if not recent_dirs:
        print("Error: No benchmark directories found from the last 24 hours.")
        sys.exit(1)

    # Find directory with most recently modified .md file
    latest_dir = None
    latest_time = 0

    for d in recent_dirs:
        # Look for .md files in subdirectories
        for md_file in d.glob("*/exercises/practice/*/.*.md"):
            if md_file.is_file():
                mtime = md_file.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_dir = d

    if not latest_dir:
        print("Error: No .md files found in recent benchmark directories.")
        sys.exit(1)

    print(f"Using the most recently updated benchmark directory: {latest_dir.name}")
    return latest_dir


def show_stats(dirnames, graphs, stats_languages=None):
    raw_rows = []
    for dirname in dirnames:
        row = summarize_results(dirname, stats_languages)
        raw_rows.append(row)

    # return

    seen = dict()
    rows = []
    for row in raw_rows:
        if not row:
            continue

        if row.completed_tests != row.total_tests:
            print(
                f"Warning: {row.dir_name} is incomplete: {row.completed_tests} of {row.total_tests}"
            )

        try:
            kind = (row.model, row.edit_format)
        except AttributeError:
            return

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
    dirnames: Optional[List[str]] = typer.Argument(None, help="Directory names"),
    graphs: bool = typer.Option(False, "--graphs", help="Generate graphs"),
    model: str = typer.Option("gpt-3.5-turbo", "--model", "-m", help="Model name"),
    sleep: float = typer.Option(
        0, "--sleep", help="Sleep seconds between tests when single threaded"
    ),
    languages: str = typer.Option(
        None, "--languages", "-l", help="Only run tests for specific languages (comma separated)"
    ),
    edit_format: str = typer.Option(None, "--edit-format", "-e", help="Edit format"),
    editor_model: str = typer.Option(None, "--editor-model", help="Editor model name"),
    editor_edit_format: str = typer.Option(None, "--editor-edit-format", help="Editor edit format"),
    replay: str = typer.Option(
        None,
        "--replay",
        help="Replay previous .aider.chat.history.md responses from previous benchmark run",
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
    stats_languages: str = typer.Option(
        None,
        "--stats-languages",
        help="Only include stats for specific languages (comma separated)",
    ),
    diffs_only: bool = typer.Option(False, "--diffs", help="Just diff the provided stats dirs"),
    tries: int = typer.Option(2, "--tries", "-r", help="Number of tries for running tests"),
    threads: int = typer.Option(1, "--threads", "-t", help="Number of threads to run in parallel"),
    num_tests: int = typer.Option(-1, "--num-tests", "-n", help="Number of tests to run"),
    num_ctx: Optional[int] = typer.Option(
        None, "--num-ctx", help="Override model context window size"
    ),
    read_model_settings: str = typer.Option(
        None, "--read-model-settings", help="Load aider model settings from YAML file"
    ),
    exercises_dir: str = typer.Option(
        EXERCISES_DIR_DEFAULT, "--exercises-dir", help="Directory with exercise files"
    ),
):
    repo = git.Repo(search_parent_directories=True)
    commit_hash = repo.head.object.hexsha[:7]
    if repo.is_dirty():
        commit_hash += "-dirty"

    if stats_only and not dirnames:
        latest_dir = find_latest_benchmark_dir()
        dirnames = [str(latest_dir)]

    if dirnames is None:
        dirnames = []

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
        return show_stats(updated_dirnames, graphs, stats_languages)

    if diffs_only:
        return show_diffs(updated_dirnames)

    assert len(updated_dirnames) == 1, updated_dirnames
    dirname = updated_dirnames[0]

    if "AIDER_DOCKER" not in os.environ:
        print("Warning: benchmarking runs unvetted code from GPT, run in a docker container")
        return

    assert BENCHMARK_DNAME.exists() and BENCHMARK_DNAME.is_dir(), BENCHMARK_DNAME

    def get_exercise_dirs(base_dir, languages=None):
        """Get all exercise directories for specified languages (or all if none specified)"""
        base_dir = Path(base_dir)

        # Get available language dirs
        lang_dirs = [d for d in base_dir.iterdir() if d.is_dir()]

        # Filter to requested languages if specified
        if languages:
            requested = set(lang.strip().lower() for lang in languages.split(","))
            lang_dirs = [d for d in lang_dirs if d.name.lower() in requested]
            dump(lang_dirs)
            if not lang_dirs:
                print(f"No matching language directories found for: {languages}")
                return []

        # Get all exercise dirs under exercises/practice for each language
        exercise_dirs = []
        for lang_dir in lang_dirs:
            practice_dir = lang_dir / "exercises" / "practice"
            if practice_dir.exists():
                exercise_dirs.extend(d for d in practice_dir.iterdir() if d.is_dir())

        return exercise_dirs

    original_dname = BENCHMARK_DNAME / exercises_dir
    assert original_dname.exists() and original_dname.is_dir(), original_dname

    exercise_dirs = get_exercise_dirs(original_dname, languages)

    if not exercise_dirs:
        print("No exercise directories found")
        return 1

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
        # Only copy the practice subdirs with exercises
        os.makedirs(dirname, exist_ok=True)
        for lang_dir in original_dname.iterdir():
            if not lang_dir.is_dir():
                continue
            practice_dir = lang_dir / "exercises" / "practice"
            if practice_dir.exists():
                dest_lang_dir = dirname / lang_dir.name / "exercises" / "practice"
                os.makedirs(dest_lang_dir.parent, exist_ok=True)
                shutil.copytree(practice_dir, dest_lang_dir)
        print("...done")

    test_dnames = sorted(str(d.relative_to(original_dname)) for d in exercise_dirs)

    resource_metadata = importlib_resources.files("aider.resources").joinpath("model-metadata.json")
    model_metadata_files_loaded = models.register_litellm_models([resource_metadata])
    dump(model_metadata_files_loaded)

    if read_model_settings:
        try:
            files_loaded = models.register_models([read_model_settings])
            if verbose:
                if files_loaded:
                    print(f"Loaded model settings from: {files_loaded[0]}")
                else:
                    print(f"No model settings loaded from: {read_model_settings}")
        except Exception as e:
            print(f"Error loading model settings: {e}")
            return 1

    if keywords:
        keywords = keywords.split(",")
        test_dnames = [dn for dn in test_dnames for keyword in keywords if keyword in dn]

    random.shuffle(test_dnames)
    if num_tests > 0:
        test_dnames = test_dnames[:num_tests]

    # Don't give up when benchmarking
    LONG_TIMEOUT = 24 * 60 * 60
    sendchat.RETRY_TIMEOUT = LONG_TIMEOUT
    base_coder.RETRY_TIMEOUT = LONG_TIMEOUT

    if threads == 1:
        all_results = []
        for test_path in test_dnames:
            results = run_test(
                original_dname,
                dirname / test_path,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
                replay,
                editor_model,
                editor_edit_format,
                num_ctx,
                sleep,
            )

            all_results.append(results)
            summarize_results(dirname)
            if sleep:
                time.sleep(sleep)
    else:
        run_test_threaded = lox.thread(threads)(run_test)
        for test_path in test_dnames:
            run_test_threaded.scatter(
                original_dname,
                dirname / test_path,
                model,
                edit_format,
                tries,
                no_unit_tests,
                no_aider,
                verbose,
                commit_hash,
                replay,
                editor_model,
                editor_edit_format,
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


def load_results(dirname, stats_languages=None):
    dirname = Path(dirname)
    all_results = []

    if stats_languages:
        languages = [lang.strip().lower() for lang in stats_languages.split(",")]
        glob_patterns = [f"{lang}/exercises/practice/*/.aider.results.json" for lang in languages]
    else:
        glob_patterns = ["*/exercises/practice/*/.aider.results.json"]

    for pattern in glob_patterns:
        for fname in dirname.glob(pattern):
            try:
                results = json.loads(fname.read_text())
                all_results.append(results)
            except json.JSONDecodeError:
                print("json.JSONDecodeError", fname)
                continue
    return all_results


def summarize_results(dirname, stats_languages=None):
    all_results = load_results(dirname, stats_languages)

    res = SimpleNamespace()
    res.total_tests = len(list(Path(dirname).glob("*/exercises/practice/*")))

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

        for key in "model edit_format commit_hash editor_model editor_edit_format".split():
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
        setattr(res, f"pass_num_{i + 1}", passed_tests[i])

    print(f"- dirname: {dirname.name}")
    style = None if res.completed_tests == res.total_tests else "red"
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
    for i in range(tries):
        print(f"  pass_num_{i + 1}: {passed_tests[i]}")

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
    print(f"  total_tests: {res.total_tests}")

    if variants["model"]:
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
    editor_model,
    editor_edit_format,
    num_ctx=None,
    sleep=0,
    read_model_settings=None,
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
            # if res.get("test_timeouts", 0) > 0:
            #    print(f"{results_fname} test timeouts, redoing...")
            # else:
            return res
        except JSONDecodeError:
            print(f"{results_fname} failed to parse, redoing...")

    # Read solution and test files from config
    fnames = []
    config_file = testdir / ".meta/config.json"
    if not config_file.exists():
        raise ValueError(f"No config file found: {config_file}")

    with open(config_file) as f:
        config = json.loads(f.read())

    # Get file sets from config
    test_files = config.get("files", {}).get("test", [])
    example_files = config.get("files", {}).get("example", [])
    solution_files = set(config.get("files", {}).get("solution", []))

    # Forcibly ignore certain files not covered by test_files and example_files
    ignore_files = set(
        [
            "CMakeLists.txt",
            "Cargo.toml",
        ]
    )

    # Add all files under .meta and .docs directories
    ignore_files.update(str(p.relative_to(testdir)) for p in testdir.glob(".meta/**/*"))
    ignore_files.update(str(p.relative_to(testdir)) for p in testdir.glob(".docs/**/*"))

    # Also ignore test & example files
    ignore_files.update(test_files)
    ignore_files.update(example_files)

    # Remove any ignore files from the solution set that LLM will edit
    solution_files.difference_update(ignore_files)

    # Copy all solution files
    for file_path in solution_files:
        src = testdir / Path(file_path)
        if src.exists():
            fnames.append(src)
            # restore the original file, in case we interrupted a prev run
            # Find the original file in the language-specific practice dir
            lang_part = str(testdir).split("/exercises/practice/")[0]
            original_fname = (
                original_dname
                / Path(lang_part).name
                / "exercises"
                / "practice"
                / testdir.name
                / file_path
            )
            if original_fname.exists():
                os.makedirs(src.parent, exist_ok=True)
                shutil.copy(original_fname, src)
        else:
            print(f"Warning: Solution file not found: {src}")

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
        yes=True,
        chat_history_file=history_fname,
    )

    # weak_model_name = model_name
    weak_model_name = None

    main_model = models.Model(
        model_name,
        weak_model=weak_model_name,
        editor_model=editor_model,
        editor_edit_format=editor_edit_format,
    )

    dump(main_model.max_chat_history_tokens)

    if num_ctx:
        if not main_model.extra_params:
            main_model.extra_params = {}
        main_model.extra_params["num_ctx"] = num_ctx
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
        ignore_mentions=ignore_files,
    )
    dump(coder.ignore_mentions)

    coder.show_announcements()
    coder.get_file_mentions = lambda x: set()  # No loading of any other files

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
            errors = run_unit_tests(original_dname, testdir, history_fname, test_files)
        except subprocess.TimeoutExpired:
            # try:
            #    errors = run_unit_tests(original_dname, testdir, history_fname, test_files)
            # except subprocess.TimeoutExpired:
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
        errors = "\n".join(errors)
        instructions = errors
        instructions += prompts.test_failures.format(file_list=file_list)

    # Clean up build directories after all attempts
    # Rust target/debug
    target_dir = testdir / "target" / "debug"
    if target_dir.exists():
        try:
            shutil.rmtree(target_dir)
            if verbose:
                print(f"Cleaned up Rust target/debug directory: {target_dir}")
        except (OSError, shutil.Error, PermissionError) as e:
            if verbose:
                print(f"Failed to clean up Rust target/debug directory: {e}")

    # Java build directories
    java_build_dir = testdir / "build"
    if java_build_dir.exists():
        try:
            shutil.rmtree(java_build_dir)
            if verbose:
                print(f"Cleaned up Java build directory: {java_build_dir}")
        except (OSError, shutil.Error, PermissionError) as e:
            if verbose:
                print(f"Failed to clean up Java build directory: {e}")

    # Node.js node_modules directories
    node_modules_dir = testdir / "node_modules"
    if node_modules_dir.exists():
        try:
            shutil.rmtree(node_modules_dir)
            if verbose:
                print(f"Cleaned up Node.js node_modules directory: {node_modules_dir}")
        except (OSError, shutil.Error, PermissionError) as e:
            if verbose:
                print(f"Failed to clean up Node.js node_modules directory: {e}")

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

    if edit_format == "architect":
        results["editor_model"] = main_model.editor_model.name if main_model.editor_model else None
        results["editor_edit_format"] = main_model.editor_edit_format
    dump(results)

    results_fname.write_text(json.dumps(results, indent=4))

    return results


def run_unit_tests(original_dname, testdir, history_fname, test_files):
    timeout = 60 * 3

    # Map of file extensions to test commands
    TEST_COMMANDS = {
        ".py": ["pytest"],
        ".rs": ["cargo", "test", "--", "--include-ignored"],
        ".go": ["go", "test", "./..."],
        ".js": ["/aider/benchmark/npm-test.sh"],
        ".cpp": ["/aider/benchmark/cpp-test.sh"],
        ".java": ["./gradlew", "test"],
    }

    # Get unique file extensions from test files
    extensions = {Path(f).suffix for f in test_files}

    # Find matching test command
    command = None
    for ext in extensions:
        if ext in TEST_COMMANDS:
            command = TEST_COMMANDS[ext]
            break

    if not command:
        raise ValueError(f"No test command found for files with extensions: {extensions}")

    # Copy test files from original directory
    for file_path in test_files:
        src = original_dname / Path(*testdir.parts[-4:]) / file_path
        dst = testdir / file_path
        if src.exists():
            print("copying", src, dst)
            os.makedirs(dst.parent, exist_ok=True)
            shutil.copy(src, dst)

    # Remove @Disabled annotations from Java test files
    for file_path in test_files:
        if file_path.endswith(".java"):
            test_file = testdir / file_path
            if test_file.exists():
                content = test_file.read_text()
                content = re.sub(r"@Disabled\([^)]*\)\s*\n", "", content)
                test_file.write_text(content)

    print(" ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        cwd=testdir,
        encoding="utf-8",
        errors="replace",
    )

    success = result.returncode == 0
    res = result.stdout
    res = cleanup_test_output(res, testdir)
    dump(res)

    with history_fname.open("a") as fh:
        fh.write(f"```\n{res}\n```")

    if not success:
        print(f"Tests failed: {testdir}")
        return res


def cleanup_test_output(output, testdir):
    # remove timing info, to avoid randomizing the response to GPT
    res = re.sub(r"\bin \d+\.\d+s\b", "", output)
    res = res.replace(str(testdir), str(testdir.name))
    return res


if __name__ == "__main__":
    app()
