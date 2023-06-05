import difflib
import sys

from .dump import dump


def main():
    if len(sys.argv) != 3:
        print("Usage: python diffs.py file1 file")
        sys.exit(1)

    file_orig, file_updated = sys.argv[1], sys.argv[2]

    with open(file_orig, "r") as f:
        lines_orig = f.readlines()

    with open(file_updated, "r") as f:
        lines_updated = f.readlines()

    unified_diff = difflib.unified_diff(lines_orig, lines_updated, fromfile=file_orig, tofile=file_updated)
    for line in unified_diff:
        print(line, end="")

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
            # line only in file_orig
            num_orig += 1
        elif code == "+":
            # line only in file_updated
            pass

    dump(last_non_deleted_orig)


if __name__ == "__main__":
    main()
