import difflib
import sys

from .dump import dump  # noqa: F401


def main():
    if len(sys.argv) != 3:
        print("Usage: python diffs.py file1 file")
        sys.exit(1)

    file_orig, file_updated = sys.argv[1], sys.argv[2]

    with open(file_orig, "r") as f:
        lines_orig = f.readlines()

    with open(file_updated, "r") as f:
        lines_updated = f.readlines()

    for i in range(len(file_updated)):
        res = diff_partial_update(lines_orig, lines_updated[:i])
        print(res)
        input()


def diff_partial_update(lines_orig, lines_updated):
    """
    Given only the first part of an updated file, show the diff while
    ignoring the block of "deleted" lines that are past the end of the
    partially complete update.
    """

    # dump(lines_orig)
    # dump(lines_updated)

    last_non_deleted = find_last_non_deleted(lines_orig, lines_updated)
    # dump(last_non_deleted)
    if last_non_deleted is None:
        return ""

    lines_orig = lines_orig[:last_non_deleted]

    diff = difflib.unified_diff(lines_orig, lines_updated)
    # unified_diff = list(unified_diff)[2:]
    # dump(repr(list(diff)))

    diff = "".join(diff) + "\n"

    diff = "```diff\n" + diff + "```\n"

    # print(diff)

    return diff


def find_last_non_deleted(lines_orig, lines_updated):
    diff = list(difflib.ndiff(lines_orig, lines_updated))

    num_orig = 0
    last_non_deleted_orig = None

    for line in diff:
        # print(f"{num_orig:2d} {num_updated:2d} {line}", end="")
        code = line[0]
        if code == " ":
            num_orig += 1
            last_non_deleted_orig = num_orig
        elif code == "-":
            # line only in orig
            num_orig += 1
        elif code == "+":
            # line only in updated
            pass

    return last_non_deleted_orig


if __name__ == "__main__":
    main()
