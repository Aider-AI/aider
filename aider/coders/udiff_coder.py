import difflib
from itertools import groupby
from pathlib import Path

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .search_replace import (
    SearchTextNotUnique,
    all_preprocs,
    diff_lines,
    flexible_search_and_replace,
    search_and_replace,
)
from .udiff_prompts import UnifiedDiffPrompts

no_match_error = """UnifiedDiffNoMatch: hunk failed to apply!

{path} does not contain lines that match the diff you provided!
Try again.
DO NOT skip blank lines, comments, docstrings, etc!
The diff needs to apply cleanly to the lines in {path}!

{path} does not contain these {num_lines} exact lines in a row:
```
{original}```
"""


not_unique_error = """UnifiedDiffNotUnique: hunk failed to apply!

{path} contains multiple sets of lines that match the diff you provided!
Try again.
Use additional ` ` lines to provide context that uniquely indicates which code needs to be changed.
The diff needs to apply to a unique set of lines in {path}!

{path} contains multiple copies of these {num_lines} lines:
```
{original}```
"""

other_hunks_applied = (
    "Note: some hunks did apply successfully. See the updated source code shown above.\n\n"
)


class UnifiedDiffCoder(Coder):
    edit_format = "udiff"

    def __init__(self, *args, **kwargs):
        self.gpt_prompts = UnifiedDiffPrompts()
        super().__init__(*args, **kwargs)

    def get_edits(self):
        content = self.partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        raw_edits = list(find_diffs(content))

        last_path = None
        edits = []
        for path, hunk in raw_edits:
            if path:
                last_path = path
            else:
                path = last_path
            edits.append((path, hunk))

        return edits

    def apply_edits(self, edits):
        seen = set()
        uniq = []
        for path, hunk in edits:
            hunk = normalize_hunk(hunk)
            if not hunk:
                continue

            this = [path + "\n"] + hunk
            this = "".join(this)

            if this in seen:
                continue
            seen.add(this)

            uniq.append((path, hunk))

        errors = []
        for path, hunk in uniq:
            full_path = self.abs_root_path(path)
            content = self.io.read_text(full_path)

            original, _ = hunk_to_before_after(hunk)

            try:
                content = do_replace(full_path, content, hunk)
            except SearchTextNotUnique:
                errors.append(
                    not_unique_error.format(
                        path=path, original=original, num_lines=len(original.splitlines())
                    )
                )
                continue

            if not content:
                errors.append(
                    no_match_error.format(
                        path=path, original=original, num_lines=len(original.splitlines())
                    )
                )
                continue

            # SUCCESS!
            self.io.write_text(full_path, content)

        if errors:
            errors = "\n\n".join(errors)
            if len(errors) < len(uniq):
                errors += other_hunks_applied
            raise ValueError(errors)


def do_replace(fname, content, hunk):
    fname = Path(fname)

    before_text, after_text = hunk_to_before_after(hunk)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()
        content = ""

    if content is None:
        return

    # TODO: handle inserting into new file
    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
        return new_content

    new_content = None

    new_content = apply_hunk(content, hunk)
    if new_content:
        return new_content


def collapse_repeats(s):
    return "".join(k for k, g in groupby(s))


def apply_hunk(content, hunk):
    before_text, after_text = hunk_to_before_after(hunk)

    res = directly_apply_hunk(content, hunk)
    if res:
        return res

    hunk = make_new_lines_explicit(content, hunk)

    # just consider space vs not-space
    ops = "".join([line[0] for line in hunk])
    ops = ops.replace("-", "x")
    ops = ops.replace("+", "x")
    ops = ops.replace("\n", " ")

    cur_op = " "
    section = []
    sections = []

    for i in range(len(ops)):
        op = ops[i]
        if op != cur_op:
            sections.append(section)
            section = []
            cur_op = op
        section.append(hunk[i])

    sections.append(section)
    if cur_op != " ":
        sections.append([])

    all_done = True
    for i in range(2, len(sections), 2):
        preceding_context = sections[i - 2]
        changes = sections[i - 1]
        following_context = sections[i]

        res = apply_partial_hunk(content, preceding_context, changes, following_context)
        if res:
            content = res
        else:
            all_done = False
            # FAILED!
            # this_hunk = preceding_context + changes + following_context
            break

    if all_done:
        return content


def flexi_just_search_and_replace(texts):
    strategies = [
        (search_and_replace, all_preprocs),
    ]

    return flexible_search_and_replace(texts, strategies)


def make_new_lines_explicit(content, hunk):
    before, after = hunk_to_before_after(hunk)

    diff = diff_lines(before, content)

    back_diff = []
    for line in diff:
        if line[0] == "+":
            continue
        # if line[0] == "-":
        #    line = "+" + line[1:]

        back_diff.append(line)

    new_before = directly_apply_hunk(before, back_diff)
    if not new_before:
        return hunk

    if len(new_before.strip()) < 10:
        return hunk

    before = before.splitlines(keepends=True)
    new_before = new_before.splitlines(keepends=True)
    after = after.splitlines(keepends=True)

    if len(new_before) < len(before) * 0.66:
        return hunk

    new_hunk = difflib.unified_diff(new_before, after, n=max(len(new_before), len(after)))
    new_hunk = list(new_hunk)[3:]

    return new_hunk


def cleanup_pure_whitespace_lines(lines):
    res = [
        line if line.strip() else line[-(len(line) - len(line.rstrip("\r\n")))] for line in lines
    ]
    return res


def normalize_hunk(hunk):
    before, after = hunk_to_before_after(hunk, lines=True)

    before = cleanup_pure_whitespace_lines(before)
    after = cleanup_pure_whitespace_lines(after)

    diff = difflib.unified_diff(before, after, n=max(len(before), len(after)))
    diff = list(diff)[3:]
    return diff


def directly_apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)

    if not before:
        return

    before_lines, _ = hunk_to_before_after(hunk, lines=True)
    before_lines = "".join([line.strip() for line in before_lines])

    # Refuse to do a repeated search and replace on a tiny bit of non-whitespace context
    if len(before_lines) < 10 and content.count(before) > 1:
        return

    try:
        new_content = flexi_just_search_and_replace([before, after, content])
    except SearchTextNotUnique:
        new_content = None

    return new_content


def apply_partial_hunk(content, preceding_context, changes, following_context):
    len_prec = len(preceding_context)
    len_foll = len(following_context)

    use_all = len_prec + len_foll

    # if there is a - in the hunk, we can go all the way to `use=0`
    for drop in range(use_all + 1):
        use = use_all - drop

        for use_prec in range(len_prec, -1, -1):
            if use_prec > use:
                continue

            use_foll = use - use_prec
            if use_foll > len_foll:
                continue

            if use_prec:
                this_prec = preceding_context[-use_prec:]
            else:
                this_prec = []

            this_foll = following_context[:use_foll]

            res = directly_apply_hunk(content, this_prec + changes + this_foll)
            if res:
                return res


def find_diffs(content):
    # We can always fence with triple-quotes, because all the udiff content
    # is prefixed with +/-/space.

    if not content.endswith("\n"):
        content = content + "\n"

    lines = content.splitlines(keepends=True)
    line_num = 0
    edits = []
    while line_num < len(lines):
        while line_num < len(lines):
            line = lines[line_num]
            if line.startswith("```diff"):
                line_num, these_edits = process_fenced_block(lines, line_num + 1)
                edits += these_edits
                break
            line_num += 1

    # For now, just take 1!
    # edits = edits[:1]

    return edits


def process_fenced_block(lines, start_line_num):
    for line_num in range(start_line_num, len(lines)):
        line = lines[line_num]
        if line.startswith("```"):
            break

    block = lines[start_line_num:line_num]
    block.append("@@ @@")

    if block[0].startswith("--- ") and block[1].startswith("+++ "):
        # Extract the file path, considering that it might contain spaces
        fname = block[1][4:].strip()
        block = block[2:]
    else:
        fname = None

    edits = []

    keeper = False
    hunk = []
    op = " "
    for line in block:
        hunk.append(line)
        if len(line) < 2:
            continue

        if line.startswith("+++ ") and hunk[-2].startswith("--- "):
            if hunk[-3] == "\n":
                hunk = hunk[:-3]
            else:
                hunk = hunk[:-2]

            edits.append((fname, hunk))
            hunk = []
            keeper = False

            fname = line[4:].strip()
            continue

        op = line[0]
        if op in "-+":
            keeper = True
            continue
        if op != "@":
            continue
        if not keeper:
            hunk = []
            continue

        hunk = hunk[:-1]
        edits.append((fname, hunk))
        hunk = []
        keeper = False

    return line_num + 1, edits


def hunk_to_before_after(hunk, lines=False):
    before = []
    after = []
    op = " "
    for line in hunk:
        if len(line) < 2:
            op = " "
            line = line
        else:
            op = line[0]
            line = line[1:]

        if op == " ":
            before.append(line)
            after.append(line)
        elif op == "-":
            before.append(line)
        elif op == "+":
            after.append(line)

    if lines:
        return before, after

    before = "".join(before)
    after = "".join(after)

    return before, after
