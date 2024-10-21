"""
This script compares two test report files and analyzes the changes in test performance.
It categorizes tests as improved, worsened, stable, or present in only one of the reports.
"""

def parse_report(file_path: str) -> dict[str, int]:
    """
    Parse a report file and extract test results.

    Args:
    file_path (str): Path to the report file.

    Returns:
    dict[str, int]: A dictionary where keys are test names and values are the number of failed runs.

    The function reads the file line by line, looking for lines that start with a number or a minus sign.
    These lines are expected to be in the format: "failed_attempts,test_name".
    """
    results = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and (line[0].isnumeric() or line[0] == '-'):
                failed_attempts, test_name = line.strip().split(',')
                results[test_name.strip()] = int(failed_attempts)
    return results


def compare_reports(report1: dict[str, int], report2: dict[str, int]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    """
    Compare two test reports and categorize the changes.

    Args:
    report1 (dict[str, int]): First report, where keys are test names and values are failed attempt counts.
    report2 (dict[str, int]): Second report, in the same format as report1.

    Returns:
    tuple[list[str], list[str], list[str], list[str], list[str]]: A tuple containing lists of:
        - improved tests
        - worsened tests
        - stable tests
        - tests only in report1
        - tests only in report2

    Tests are categorized based on their presence in the reports and changes in failed attempt counts.
    Negative failed run counts are treated specially, indicating a different kind of failure.
    """
    improved = []
    worsened = []
    stable = []
    only_1 = []
    only_2 = []

    all_tests = set(report1.keys()) | set(report2.keys())

    for test in sorted(all_tests):
        failed_attempts_1 = report1.get(test)
        failed_attempts_2 = report2.get(test)

        if failed_attempts_1 is None:
            only_2.append(test)
            continue
        elif failed_attempts_2 is None:
            only_1.append(test)
            continue
        elif failed_attempts_1 < 0 and failed_attempts_2 < 0:
            stable.append(test)
            continue

        if failed_attempts_1 < 0:
            improved.append(test)
        elif failed_attempts_2 < 0:
            worsened.append(test)
        elif failed_attempts_2 < failed_attempts_1:
            improved.append(test)
        elif failed_attempts_2 > failed_attempts_1:
            worsened.append(test)
        else:
            stable.append(test)

    return improved, worsened, stable, only_1, only_2

def main(file_path1: str, file_path2: str):
    """
    Main function to compare two test report files and print the analysis.

    Args:
    file_path1 (str): Path to the first report file.
    file_path2 (str): Path to the second report file.

    This function parses both report files, compares them, and prints a detailed analysis
    of how tests have changed between the two reports. It categorizes tests as improved,
    worsened, stable, or present in only one report, and provides a summary count for each category.
    """
    report1 = parse_report(file_path1)
    report2 = parse_report(file_path2)

    improved, worsened, stable, only_1, only_2 = compare_reports(report1, report2)

    for test in only_1:
        failed_attempts = report1[test]
        print(f"<{'-' if failed_attempts < 0 else '+'}{test}: {failed_attempts}")

    for test in only_2:
        failed_attempts = report2[test]
        print(f">{'-' if failed_attempts < 0 else '+'}{test}: {failed_attempts}")

    for test in improved:
        print(f"+{test}: {report1.get(test, 'N/A')} -> {report2.get(test, 'N/A')}")

    for test in worsened:
        print(f"-{test}: {report1.get(test, 'N/A')} -> {report2.get(test, 'N/A')}")

    for test in stable:
        failed_attempts_2 = report2.get(test)
        print(f"={test}: {report1.get(test)}{f" -> {failed_attempts_2}" if failed_attempts_2 is None or failed_attempts_2 < 0 else ''}")

    print(f"\n+ {len(improved)}")
    print(f"- {len(worsened)}")
    print(f"= {len(stable)}")
    print(f"< {len(only_1)}")
    print(f"> {len(only_2)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python benchmark_diff.py <file_path1> <file_path2>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
