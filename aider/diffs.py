import difflib
import sys

from .dump import dump  # noqa: F401


def main():
    if len(sys.argv) != 3:
        print("Usage: python diffs.py file1 file")
        sys.exit(1)

    file_orig, file_updated = sys.argv[1], sys.argv[2]

    with open(file_orig, "r", encoding="utf-8") as f:
        lines_orig = f.readlines()

    with open(file_updated, "r", encoding="utf-8") as f:
        lines_updated = f.readlines()

    for i in range(len(file_updated)):
        res = diff_partial_update(lines_orig, lines_updated[:i])
        print(res)
        input()


def create_progress_bar(percentage):
    block = "█"
    empty = "░"
    total_blocks = 30
    filled_blocks = int(total_blocks * percentage // 100)
    empty_blocks = total_blocks - filled_blocks
    bar = block * filled_blocks + empty * empty_blocks
    return bar


def assert_newlines(lines):
    if not lines:
        return
    for line in lines[:-1]:
        assert line and line[-1] == "\n", line


def diff_partial_update(lines_orig, lines_updated, final=False, fname=None):
    """
    Given only the first part of an updated file, show the diff while
    ignoring the block of "deleted" lines that are past the end of the
    partially complete update.
    """

    # dump(lines_orig)
    # dump(lines_updated)

    assert_newlines(lines_orig)
    assert_newlines(lines_orig)

    num_orig_lines = len(lines_orig)

    if final:
        last_non_deleted = num_orig_lines
    else:
        last_non_deleted = find_last_non_deleted(lines_orig, lines_updated)

    # dump(last_non_deleted)
    if last_non_deleted is None:
        return ""

    if num_orig_lines:
        pct = last_non_deleted * 100 / num_orig_lines
    else:
        pct = 50
    bar = create_progress_bar(pct)
    bar = f" {last_non_deleted:3d} / {num_orig_lines:3d} lines [{bar}] {pct:3.0f}%\n"

    lines_orig = lines_orig[:last_non_deleted]

    if not final:
        lines_updated = lines_updated[:-1] + [bar]

    diff = difflib.unified_diff(lines_orig, lines_updated, n=5)

    diff = list(diff)[2:]

    diff = "".join(diff)
    if not diff.endswith("\n"):
        diff += "\n"

    for i in range(3, 10):
        backticks = "`" * i
        if backticks not in diff:
            break

    show = f"{backticks}diff\n"
    if fname:
        show += f"--- {fname} original\n"
        show += f"+++ {fname} updated\n"

    show += diff

    show += f"{backticks}\n\n"

    # print(diff)

    return show


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
