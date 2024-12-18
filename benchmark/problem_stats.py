#!/usr/bin/env python

import argparse
import json
from collections import defaultdict
from pathlib import Path

import yaml


def get_dirs_from_leaderboard():
    # Load the leaderboard data
    with open("aider/website/_data/edit_leaderboard.yml") as f:
        leaderboard = yaml.safe_load(f)
    return [(entry["dirname"], entry["model"]) for entry in leaderboard]


def load_results(dirname):
    """Load all result files from a benchmark directory"""
    dirname = Path(dirname)
    benchmark_dir = Path("tmp.benchmarks") / dirname
    if not benchmark_dir.exists():
        return None

    all_results = []
    # Look in language subdirectories under exercises/practice
    for fname in benchmark_dir.glob("*/exercises/practice/*/.aider.results.json"):
        try:
            results = json.loads(fname.read_text())
            # Add language info to results
            lang = fname.parts[-4]  # Get language from path
            results["language"] = lang
            all_results.append(results)
        except json.JSONDecodeError:
            print(f"Failed to parse {fname}")
            continue
    return all_results


def analyze_exercise_solutions(dirs=None, topn=None):
    if dirs is None:
        # Use leaderboard data if no directories specified
        dir_entries = get_dirs_from_leaderboard()
    else:
        # Use provided directories, with dirname as model name
        dir_entries = [(d, d) for d in dirs]

    # Filter out entries that don't load and sort by pass rate
    valid_entries = []
    for dirname, model in dir_entries:
        results = load_results(dirname)
        if results:
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
            all_exercises.update(result["testcase"] for result in results)

    for (dirname, model), results, _ in valid_entries:
        if not results:
            print(f"Could not load results for {dirname}")
            continue

        for result in results:
            testcase = result.get("testcase")
            if not testcase:
                continue

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

    # Group exercises by language
    by_language = defaultdict(list)
    for testcase in all_exercises:
        # Find language for this testcase from results
        lang = next(
            (r["language"] for r in next(iter(valid_entries))[1] if r["testcase"] == testcase),
            "unknown",
        )
        by_language[lang].append(testcase)

    # Sort languages
    sorted_languages = sorted(by_language.keys())

    # Calculate max lengths for alignment
    max_name_len = max(len(testcase) for testcase in all_exercises)
    total_models = len(valid_entries)

    # Print exercises grouped by language
    for lang in sorted_languages:
        print(f"\n{lang.upper()}:")
        lang_exercises = [(ex, exercise_solutions[ex]) for ex in by_language[lang]]
        # Sort by number of models that solved each exercise
        lang_exercises.sort(key=lambda x: len(x[1]), reverse=True)

        for i, (testcase, models) in enumerate(lang_exercises, 1):
            num_solved = len(models)
            percent = (num_solved / total_models) * 100
            print(f"{i:>3}. {testcase:<{max_name_len}} : {num_solved:>3} solved ({percent:>5.1f}%)")

    print("\nSummary:")
    solved_at_least_once = len([ex for ex, models in exercise_solutions.items() if models])
    print(f"Total exercises solved at least once: {solved_at_least_once}")
    print(f"Never solved by any model: {never_solved}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topn", type=int, help="Only consider top N models by pass rate")
    parser.add_argument(
        "dirs", nargs="*", help="Directories to analyze (optional, defaults to leaderboard entries)"
    )
    args = parser.parse_args()

    analyze_exercise_solutions(args.dirs if args.dirs else None, args.topn)
