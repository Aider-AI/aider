#!/usr/bin/env python

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

import yaml

from aider.dump import dump  # noqa

HARD_SET_NUM = 3  # Number of models that defines the hard set threshold


def get_dirs_from_leaderboard():
    # Load the leaderboard data
    with open("aider/website/_data/edit_leaderboard.yml") as f:
        leaderboard = yaml.safe_load(f)
    return [(entry["dirname"], entry["model"]) for entry in leaderboard]


def load_results(dirname):
    """Load all result files from a benchmark directory"""
    dirname = Path(dirname)

    benchmark_dir = dirname
    if not benchmark_dir.exists():
        benchmark_dir = Path("tmp.benchmarks") / dirname
        if not benchmark_dir.exists():
            return None

    all_results = []
    parse_errors = []  # Track which exercises had parse errors for this model

    # Look in language subdirectories under exercises/practice
    for fname in benchmark_dir.glob("*/exercises/practice/*/.aider.results.json"):
        error = False
        try:
            results = json.loads(fname.read_text())
            error = "testcase" not in results
            if not error:
                # Add language info to results
                lang = fname.parts[-5]  # Get language from path
                results["language"] = lang
                all_results.append(results)

        except json.JSONDecodeError:
            error = True

        if error:
            # Track the parse error for this exercise/model combination
            lang = fname.parts[-5]
            exercise = f"{fname.parts[-2]}/{lang}"  # Use directory name as testcase
            parse_errors.append(exercise)
            print(f"Bad results file {fname}")
            continue

    return all_results, parse_errors


def analyze_exercise_solutions(dirs=None, topn=None, copy_hard_set=False):
    PARSE_ERROR_M = 4  # Threshold for number of parse errors to DQ an exercise

    if dirs is None:
        # Use leaderboard data if no directories specified
        dir_entries = get_dirs_from_leaderboard()
    else:
        # Use provided directories, with dirname as model name
        dir_entries = [(d, d) for d in dirs]

    # Filter out entries that don't load and sort by pass rate
    valid_entries = []
    parse_errors_by_model = {}  # Track which exercises had parse errors for each model

    dump(dir_entries)

    for dirname, model in dir_entries:
        results_data = load_results(dirname)

        if results_data:
            results, model_parse_errors = results_data
            parse_errors_by_model[model] = set(model_parse_errors)
            # Calculate pass rate for sorting when using custom dirs
            if dirs is not None:
                pass_rate = sum(
                    1 for r in results if r.get("tests_outcomes", []) and r["tests_outcomes"][-1]
                ) / len(results)
            else:
                # Use existing pass rate from leaderboard
                pass_rate = next(
                    (
                        entry["pass_rate_2"]
                        for entry in yaml.safe_load(
                            open("aider/website/_data/edit_leaderboard.yml")
                        )
                        if entry["dirname"] == dirname
                    ),
                    0,
                )
            valid_entries.append(((dirname, model), results, float(pass_rate)))

    # Sort by pass rate and take top N if specified
    valid_entries.sort(key=lambda x: x[2], reverse=True)
    if topn:
        valid_entries = valid_entries[:topn]

    # Get all exercise names from a complete run
    all_exercises = set()
    exercise_solutions = defaultdict(list)

    # Get all unique exercise names from all results
    all_exercises = set()
    for (dirname, model), results, _ in valid_entries:
        if results:
            for result in results:
                try:
                    all_exercises.add(result["testcase"] + "/" + result["language"])
                except KeyError:
                    print(f"Warning: Missing testcase in {dirname}", json.dumps(result, indent=4))

    for (dirname, model), results, _ in valid_entries:
        if not results:
            print(f"Could not load results for {dirname}")
            continue

        for result in results:
            testcase = result.get("testcase")
            if not testcase:
                continue
            lang = result.get("language")
            if not lang:
                continue

            testcase = f"{testcase}/{lang}"
            # Consider it solved if the last test attempt passed
            tests_outcomes = result.get("tests_outcomes", [])
            if tests_outcomes and tests_outcomes[-1]:
                exercise_solutions[testcase].append(model)

    # Calculate never solved exercises
    never_solved = len(all_exercises - set(exercise_solutions.keys()))

    # Print per-exercise statistics
    print("\nExercise Solution Statistics:")
    print("-" * 40)

    # Add exercises that were never solved
    for exercise in all_exercises:
        if exercise not in exercise_solutions:
            exercise_solutions[exercise] = []

    # Create list of (language, exercise) pairs with solution stats
    exercise_stats = []
    total_models = len(valid_entries)

    for testcase in all_exercises:
        # Language is already in the testcase string
        lang = testcase.split("/")[0]  # First part is the language
        models = exercise_solutions[testcase]
        num_solved = len(models)
        percent = (num_solved / total_models) * 100
        testcase = testcase.replace("exercises/", "")  # Remove the exercises/ prefix
        # Remove duplicate language prefix (e.g. javascript/javascript/ -> javascript/)
        if testcase.startswith(f"{lang}/{lang}/"):
            testcase = testcase[len(lang) + 1 :]
        exercise_stats.append((lang, testcase, num_solved, percent))

    # Sort all exercises by solve rate, then by exercise name
    exercise_stats.sort(
        key=lambda x: (-x[2], x[1])
    )  # -x[2] for descending solve rate, x[1] for ascending exercise name

    # Calculate max lengths for alignment after cleaning up paths
    max_name_len = max(len(f"{lang}/{testcase}") for lang, testcase, _, _ in exercise_stats)

    # Print all exercises sorted by solve rate
    print("\nAll Exercises (sorted by solve rate):")
    for i, (lang, testcase, num_solved, percent) in enumerate(exercise_stats, 1):
        print(f"{i:>3}. {testcase:<{max_name_len}} : {num_solved:>3} solved ({percent:>5.1f}%)")

    print("\nSummary:")
    solved_at_least_once = len([ex for ex, models in exercise_solutions.items() if models])
    solved_by_none = never_solved
    solved_by_all = len(
        [ex for ex, models in exercise_solutions.items() if len(models) == total_models]
    )

    print(f"Total exercises solved at least once: {solved_at_least_once}")
    print(f"Never solved by any model: {solved_by_none}")
    if solved_by_none > 0:
        print("\nExercises never solved by any model:")
        unsolved = [ex for ex, models in exercise_solutions.items() if not models]
        for ex in sorted(unsolved):
            # Split into language and exercise parts
            lang, exercise = ex.split("/")
            # Reconstruct path in desired format
            formatted_path = f"{lang}/exercises/practice/{exercise}"
            print(f"  {formatted_path}")
    print(f"\nSolved by all models: {solved_by_all}")
    print(
        f"Total exercises: {len(all_exercises)} = {solved_by_none} (none) + {solved_by_all} (all) +"
        f" {len(all_exercises) - solved_by_none - solved_by_all} (some)"
    )

    # Distribution table of how many models solved each exercise
    print("\nDistribution of solutions:")
    print("Models  Exercises  Cumulative  RevCumulative")
    print("-" * 50)
    counts = [0] * (total_models + 1)
    for ex, models in exercise_solutions.items():
        counts[len(models)] += 1

    cumsum = 0
    revcumsum = sum(counts)  # Start with total number of exercises
    for i, count in enumerate(counts):
        cumsum += count
        print(f"{i:>6d}  {count:>9d}  {cumsum:>10d}  {revcumsum:>12d}")
        revcumsum -= count  # Decrement the reverse cumulative sum

    # Count parse errors per exercise
    parse_error_counts = defaultdict(int)
    for model_errors in parse_errors_by_model.values():
        for exercise in model_errors:
            parse_error_counts[exercise] += 1

    # Find exercises to disqualify based on parse error threshold
    disqualified_exercises = {
        exercise for exercise, count in parse_error_counts.items() if count >= PARSE_ERROR_M
    }

    if disqualified_exercises:
        print(
            f"\nDisqualified {len(disqualified_exercises)} exercises with {PARSE_ERROR_M}+ parse"
            " errors:"
        )
        for ex in sorted(disqualified_exercises):
            print(f"  {ex} ({parse_error_counts[ex]} parse errors)")

    # Collect the hard set (exercises solved by HARD_SET_NUM or fewer models)
    print(f"\nHard Set Analysis (exercises solved by ≤{HARD_SET_NUM} models):")
    print("-" * 60)
    hard_set = {
        ex
        for ex, models in exercise_solutions.items()
        if len(models) <= HARD_SET_NUM and ex not in disqualified_exercises
    }
    print(f"Total hard set exercises: {len(hard_set)}")

    # Count total problems, unsolved problems, and hard set problems by language
    lang_totals = defaultdict(int)
    lang_unsolved = defaultdict(int)
    lang_hard_set = defaultdict(int)

    for exercise in all_exercises:
        lang = exercise.split("/")[1]  # Get language from path
        lang_totals[lang] += 1
        if not exercise_solutions[exercise]:  # No models solved this exercise
            lang_unsolved[lang] += 1
        if exercise in hard_set:  # Exercise is in the hard set
            lang_hard_set[lang] += 1

    print("\nUnsolved and hard set problems by language:")
    print(f"{'Language':<12} {'Unsolved':>8} {'Hard Set':>9} {'Total':>7} {'%hardUnsolved':>8}")
    print("-" * 47)
    for lang in sorted(lang_totals.keys()):
        count = lang_unsolved[lang]
        hard = lang_hard_set[lang]
        total = lang_totals[lang]
        pct = (count / hard) * 100 if hard else -1
        print(f"{lang:<12} {count:>8} {hard:>9} {total:>7} {pct:>7.1f}%")
    print()

    # For each model, compute performance on hard set
    model_hard_stats = []
    for (dirname, model), results, _ in valid_entries:
        if not results:
            continue

        solved_hard = 0
        for result in results:
            testcase = result.get("testcase")
            if not testcase:
                continue
            lang = result.get("language")
            if not lang:
                continue

            testcase = f"{testcase}/{lang}"
            if testcase in hard_set:
                tests_outcomes = result.get("tests_outcomes", [])
                if tests_outcomes and tests_outcomes[-1]:
                    solved_hard += 1

        pct = (solved_hard / len(hard_set)) * 100
        model_hard_stats.append((model, solved_hard, pct))

    # Sort by number solved
    model_hard_stats.sort(key=lambda x: x[1], reverse=True)

    print("\nModel performance on hard set:")
    print(f"{'Model':<55} {'Solved':<8} {'Percent':>7}")
    print("-" * 50)
    for model, solved, pct in model_hard_stats:
        print(f"{model:<55} {solved:>6d}   {pct:>6.1f}%")

    if copy_hard_set:
        # Create hard set directory
        src_dir = Path("tmp.benchmarks/exercism")
        dst_dir = Path("tmp.benchmarks/exercism-polyglot")

        if dst_dir.exists():
            print(f"\nError: Destination directory {dst_dir} already exists")
            return

        print(f"\nCopying hard set problems to {dst_dir}...")

        # Create a set of (exercise, language) pairs from hard_set
        hard_set_pairs = {tuple(exercise.split("/")) for exercise in hard_set}

        # Copy each hard set problem's directory
        copied_by_lang = defaultdict(int)
        for lang_dir in src_dir.glob("*/exercises/practice"):
            if not lang_dir.is_dir():
                continue

            lang = lang_dir.parts[-3]  # Get language from path
            for problem_dir in lang_dir.glob("*"):
                if (problem_dir.name, lang) in hard_set_pairs:
                    rel_path = problem_dir.relative_to(src_dir)
                    dst_path = dst_dir / rel_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(problem_dir, dst_path)
                    copied_by_lang[lang] += 1

        total_copied = sum(copied_by_lang.values())
        print(f"\nCopied {total_copied} hard set problems:")
        for lang in sorted(copied_by_lang):
            print(f"  {lang}: {copied_by_lang[lang]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topn", type=int, help="Only consider top N models by pass rate")
    parser.add_argument(
        "dirs", nargs="*", help="Directories to analyze (optional, defaults to leaderboard entries)"
    )
    parser.add_argument(
        "--copy-hard-set",
        action="store_true",
        help="Copy hard set problems to tmp.benchmarks/exercism-polygot",
    )
    args = parser.parse_args()

    analyze_exercise_solutions(args.dirs if args.dirs else None, args.topn, args.copy_hard_set)
