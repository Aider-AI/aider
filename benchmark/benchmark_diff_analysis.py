#!/usr/bin/env python
"""
This script compares two benchmark run dir and analyzes the changes in test performance.
It categorizes tests as improved, worsened, stable, or present in only one of the benchmark runs.
"""
import os
import subprocess
from functools import total_ordering
from typing import NamedTuple, Union


@total_ordering
class AiderTestResult(NamedTuple):
    failed_attempt_count: int
    name: str
    cost: float
    duration: float
    test_timeouts: int
    num_error_outputs: int
    num_user_asks: int
    num_exhausted_context_windows: int
    num_malformed_responses: int
    syntax_errors: int
    indentation_errors: int
    lazy_comments: int

    def __eq__(self, other: Union['AiderTestResult', int]) -> bool:
        if isinstance(other, int):
            return self.failed_attempt_count == other
        if isinstance(other, AiderTestResult):
            return self.failed_attempt_count == other.failed_attempt_count
        return NotImplemented

    def __lt__(self, other: Union['AiderTestResult', int]) -> bool:
        if isinstance(other, int):
            return self.failed_attempt_count < other
        if isinstance(other, AiderTestResult):
            return self.failed_attempt_count < other.failed_attempt_count
        return NotImplemented

    def __int__(self) -> int:
        return self.failed_attempt_count


def create_aider_test_result(csv_string):
    # Split the string into a list of values
    values = csv_string.split(',')

    # Ensure we have the correct number of values
    if len(values) != len(AiderTestResult._fields):
        raise ValueError(f"Expected {len(AiderTestResult._fields)} values, but got {len(values)}")

    # Convert values to appropriate types
    converted_values = {}
    for i, (field, value) in enumerate(zip(AiderTestResult._fields, values)):
        try:
            match field:
                case 'name':
                    value = value.strip()
                case x if x.endswith('count') or x.endswith('s'):
                    value = int(value)
                case _:
                    value = float(value)
        except ValueError:
            # If conversion fails, keep the original string
            pass
        converted_values[field] = value

    return AiderTestResult(**converted_values)


def parse_benchmark_dir(benchmark_dir: str) -> list[AiderTestResult]:
    """
    Parse a benchmark run dir and extract test results.

    Args:
    benchmark_dir (str): Path to the benchmark run dir.

    Returns:
    list[AiderTestResult]: A list of test resulkts

    The function reads the file line by line, looking for lines that start with a number or a minus sign.
    These lines are expected to be in the format: "failed_attempts,test_name".
    """

    results = []
    ls = benchmark_ls(benchmark_dir)
    for line in ls.splitlines():
        line = line.strip()
        if line and (line[0].isnumeric() or line[0] == '-'):
            results.append(create_aider_test_result(line))
    return results


def compare_benchmark_runs(benchmark_run_1: dict[str, AiderTestResult], benchmark_run_2: dict[str, AiderTestResult]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    """
    Compare two benchmark run dirs and categorize the changes.

    Args:
    benchmark_run_1 (dict[str, AiderTestResult]): First  test result from first benchmark run, where keys are test names.
    benchmark_run_2 (dict[str, AiderTestResult]): Second test result from first benchmark run, in the same format as above.

    Returns:
    tuple[list[str], list[str], list[str], list[str], list[str]]: A tuple containing lists of:
        - tests only in benchmark_run_1
        - tests only in benchmark_run_2
        - improved tests
        - worsened tests
        - stable tests

    Tests are categorized based on their presence in the runs and changes in failed attempt counts.
    Negative failed run counts indicate the limit of failed attempts was reached and the test didn't pass.
    """
    only_1 = []
    only_2 = []
    improved = []
    worsened = []
    stable = []

    all_test_names = set(benchmark_run_1.keys()) | set(benchmark_run_2.keys())

    for test_name in sorted(all_test_names):
        test_from_run_1 = benchmark_run_1.get(test_name)
        test_from_run_2 = benchmark_run_2.get(test_name)

        if test_from_run_1 is None:
            only_2.append(test_name)
            continue
        if test_from_run_2 is None:
            only_1.append(test_name)
            continue
        if test_from_run_1 == test_from_run_2:
            stable.append(test_name)
            continue
        if test_from_run_1 < 0 and test_from_run_2 < 0:
            stable.append(test_name)
            continue

        if test_from_run_1.failed_attempt_count < 0:
            improved.append(test_name)
            continue
        if test_from_run_2 < 0:
            worsened.append(test_name)
            continue
        if test_from_run_2 < test_from_run_1:
            improved.append(test_name)
            continue
        if test_from_run_2 > test_from_run_1:
            worsened.append(test_name)
            continue
        stable.append(test_name)

    return only_1, only_2, improved, worsened, stable


def main(benchmark_dir_1: str, benchmark_dir_2: str):
    """
    Main function to compare two benchmark runs and print the analysis.

    Args:
    benchmark_dir_1 (str): Path to the first benchmark run.
    benchmark_dir_2 (str): Path to the second benchmark run.

    This function parses both benchmark runs, compares them, and prints a detailed analysis
    of how tests have changed between the two runs. It categorizes tests as improved,
    worsened, stable, or present in only one run, and provides a summary count for each category and sub-category.
    """
    print(f"--- {benchmark_dir_1.split('/')[-1]}")
    print(f"+++ {benchmark_dir_2.split('/')[-1]}")
    print("# ============= Failed Attempts per Test =============")
    print("# N >= 0: It eventually passed after N failed attempts")
    print("# N < 0 : All attempts failed and the limit was reached")
    benchmark_run_1 = {t.name: t for t in parse_benchmark_dir(benchmark_dir_1)}
    benchmark_run_2 = {t.name: t for t in parse_benchmark_dir(benchmark_dir_2)}

    (
        test_names_only_1, test_names_only_2, test_names_improved, test_names_worsened, test_names_stable
    ) = compare_benchmark_runs(benchmark_run_1, benchmark_run_2)

    test_names_only_1_passed = [t for t in test_names_only_1 if benchmark_run_1[t].failed_attempt_count >= 0]
    if test_names_only_1_passed:
        print()
        print(f"@@ REMOVED ({len(test_names_only_1_passed)} PASSED) @@")
        for test_name in test_names_only_1_passed:
            failed_attempt_count = benchmark_run_1[test_name].failed_attempt_count
            print(f"<{'-' if failed_attempt_count < 0 else '+'}{test_name}: {failed_attempt_count}")

    test_names_only_1_failed = [t for t in test_names_only_1 if benchmark_run_1[t].failed_attempt_count < 0]
    if test_names_only_1_failed:
        print()
        print(f"@@ REMOVED ({len(test_names_only_1_failed)} FAILED) @@")
        for test_name in test_names_only_1_failed:
            failed_attempt_count = benchmark_run_1[test_name].failed_attempt_count
            print(f"<{'-' if failed_attempt_count < 0 else '+'}{test_name}: {failed_attempt_count}")

    test_names_only_2_passed = [t for t in test_names_only_2 if benchmark_run_2[t].failed_attempt_count >= 0]
    if test_names_only_2_passed:
        print()
        print(f"@@ NEW ({len(test_names_only_2_passed)} PASSED) @@")
        for test_name in test_names_only_2_passed:
            failed_attempt_count = benchmark_run_2[test_name].failed_attempt_count
            print(f">{'-' if failed_attempt_count < 0 else '+'}{test_name}: {failed_attempt_count}")

    test_names_only_2_failed = [t for t in test_names_only_2 if benchmark_run_2[t].failed_attempt_count < 0]
    if test_names_only_2_failed:
        print()
        print(f"@@ NEW ({len(test_names_only_2_failed)} FAILED) @@")
        for test_name in test_names_only_2_failed:
            failed_attempt_count = benchmark_run_2[test_name].failed_attempt_count
            print(f">{'-' if failed_attempt_count < 0 else '+'}{test_name}: {failed_attempt_count}")

    test_names_improved_now_passes = [t for t in test_names_improved if benchmark_run_1[t].failed_attempt_count < 0]
    if test_names_improved_now_passes:
        print()
        print(f"@@ Improved, now PASSED ({len(test_names_improved_now_passes)}) @@")
        for test_name in test_names_improved_now_passes:
            print(f"++{test_name}: {benchmark_run_1.get(test_name).failed_attempt_count} -> {benchmark_run_2.get(test_name).failed_attempt_count}")

    test_names_improved_minor = [t for t in test_names_improved if benchmark_run_1[t].failed_attempt_count >= 0]
    if test_names_improved_minor:
        print()
        print(f"@@ Improved, minor ({len(test_names_improved_minor)}) @@")
        for test_name in test_names_improved_minor:
            print(f"+ {test_name}: {benchmark_run_1.get(test_name).failed_attempt_count} -> {benchmark_run_2.get(test_name).failed_attempt_count}")

    test_names_worsened_now_fails = [t for t in test_names_worsened if benchmark_run_2[t].failed_attempt_count < 0]
    if test_names_worsened_now_fails:
        print()
        print(f"@@ Worsened, now FAILED ({len(test_names_worsened_now_fails)}) @@")
        for test_name in test_names_worsened_now_fails:
            print(f"--{test_name}: {benchmark_run_1.get(test_name).failed_attempt_count} -> {benchmark_run_2.get(test_name).failed_attempt_count}")

    test_names_worsened_minor = [t for t in test_names_worsened if benchmark_run_2[t].failed_attempt_count >= 0]
    if test_names_worsened_minor:
        print()
        print(f"@@ Worsened, still PASSED ({len(test_names_worsened_minor)}) @@")
        for test_name in test_names_worsened_minor:
            print(f"- {test_name}: {benchmark_run_1.get(test_name).failed_attempt_count} -> {benchmark_run_2.get(test_name).failed_attempt_count}")

    test_names_stable_passed = [t for t in test_names_stable if benchmark_run_1[t].failed_attempt_count >= 0]
    if test_names_stable_passed:
        print()
        print(f"@@ Stable: PASSED ({len(test_names_stable_passed)}) @@")
        for test_name in test_names_stable_passed:
            failed_attempts_2 = benchmark_run_2.get(test_name).failed_attempt_count
            print(f"=+{test_name}: {benchmark_run_1.get(test_name).failed_attempt_count}{f" -> {failed_attempts_2}" if failed_attempts_2 is None or failed_attempts_2 < 0 else ''}")

    test_names_stable_failed = [t for t in test_names_stable if benchmark_run_1[t].failed_attempt_count < 0]
    if test_names_stable_failed:
        print()
        print(f"@@ Stable: FAILED ({len(test_names_stable_failed)}) @@")
        for test_name in test_names_stable_failed:
            failed_attempts_2 = benchmark_run_2.get(test_name).failed_attempt_count
            print(f"=-{test_name}: {benchmark_run_1.get(test_name).failed_attempt_count}{f" -> {failed_attempts_2}" if failed_attempts_2 is None or failed_attempts_2 < 0 else ''}")

    print()
    print("# =============          TOTALS          =============")
    if test_names_only_1:
        print(f"# REMOVED : {len(test_names_only_1)}")
        print(f"#    PASSED: {len(test_names_only_1_passed)}")
        print(f"#    FAILED: {len(test_names_only_1_failed)}")
    if test_names_only_2:
        print(f"# NEW     : {len(test_names_only_2)}")
        print(f"#    PASSED: {len(test_names_only_2_passed)}")
        print(f"#    FAILED: {len(test_names_only_2_failed)}")
    if test_names_improved:
        print(f"# IMPROVED: {len(test_names_improved)}")
        print(f"#    Now PASSES: {len(test_names_improved_now_passes)}")
        print(f"#    Minor     : {len(test_names_improved_minor)}")
    if test_names_worsened:
        print(f"# WORSENED: {len(test_names_worsened)}")
        print(f"#    Now FAILED: {len(test_names_worsened_now_fails)}")
        print(f"#    Minor     : {len(test_names_worsened_minor)}")
    if test_names_stable:
        print(f"# STABLE  : {len(test_names_stable)}")
        print(f"#    PASSED: {len(test_names_stable_passed)}")
        print(f"#    FAILED: {len(test_names_stable_failed)}")
    test_count_delta = len(benchmark_run_2) - len(benchmark_run_1)
    if len(benchmark_run_1) == len(benchmark_run_2):
        print(f"# TOTAL  : {len(benchmark_run_1)}")
    else:
        # In case the number of test cases differ between the 2 benchmark runs
        print(f"# TOTAL  : {len(benchmark_run_1)}{test_count_delta:+}")


def benchmark_ls(benchmark_run_dir):
    try:
        # Get the directory of the current Python file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the shell script
        script_path = os.path.join(current_dir, 'benchmark-test-info.sh')

        benchmark_run_dir = os.path.join(os.getcwd(), benchmark_run_dir)

        # Run the shell script and capture its output
        result = subprocess.run(
            [script_path, benchmark_run_dir],
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print(f"Error running the script: {e}")
        print(f"Script output: {e.output}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python benchmark_diff_analysis.py <benchmark_dir_1> <benchmark_dir_2>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
