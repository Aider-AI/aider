#!/usr/bin/env python

import argparse
import json
from collections import defaultdict
from pathlib import Path

import yaml


def load_results(dirname):
    """Load all result files from a benchmark directory"""
    dirname = Path(dirname)
    benchmark_dir = Path("tmp.benchmarks") / dirname
    if not benchmark_dir.exists():
        return None

    all_results = []
    for fname in benchmark_dir.glob("*/.aider.results.json"):
        try:
            results = json.loads(fname.read_text())
            all_results.append(results)
        except json.JSONDecodeError:
            print(f"Failed to parse {fname}")
            continue
    return all_results


def analyze_exercise_solutions(topn=None):
    # Load the leaderboard data
    with open("aider/website/_data/edit_leaderboard.yml") as f:
        leaderboard = yaml.safe_load(f)

    # Filter out entries that don't load and sort by pass rate
    valid_entries = []
    for entry in leaderboard:
        dirname = entry["dirname"]
        results = load_results(dirname)
        if results:
            valid_entries.append((entry, results))

    # Sort by pass rate and take top N if specified
    valid_entries.sort(key=lambda x: float(x[0].get("pass_rate_2", 0)), reverse=True)
    if topn:
        valid_entries = valid_entries[:topn]

    # Unpack the filtered and sorted entries
    leaderboard = [entry for entry, _ in valid_entries]

    # Get all exercise names from a complete run
    all_exercises = set()
    exercise_solutions = defaultdict(list)

    # Find a complete run to get all exercise names
    for entry in leaderboard:
        dirname = entry["dirname"]
        results = load_results(dirname)
        if results and len(results) == 133:  # Complete run
            all_exercises = {result["testcase"] for result in results}
            break

    for entry in leaderboard:
        dirname = entry["dirname"]
        model = entry["model"]

        results = load_results(dirname)
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

    # Print per-exercise statistics
    print("\nExercise Solution Statistics:")
    print("-" * 40)

    # Add exercises that were never solved
    for exercise in all_exercises:
        if exercise not in exercise_solutions:
            exercise_solutions[exercise] = []

    # Sort by number of models that solved each exercise
    sorted_exercises = sorted(exercise_solutions.items(), key=lambda x: len(x[1]), reverse=True)

    # Calculate max length for alignment
    max_name_len = max(len(testcase) for testcase in all_exercises)
    total_models = len(leaderboard)

    for i, (testcase, models) in enumerate(sorted_exercises, 1):
        num_solved = len(models)
        percent = (num_solved / total_models) * 100
        print(f"{i:>3}. {testcase:<{max_name_len}} : {num_solved:>3} solved ({percent:>5.1f}%)")

    print("\nSummary:")
    print(f"Total exercises solved at least once: {len(exercise_solutions)}")
    never_solved = 133 - len(exercise_solutions)
    print(f"Never solved by any model: {never_solved}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topn", type=int, help="Only consider top N models by pass rate")
    args = parser.parse_args()

    analyze_exercise_solutions(args.topn)
