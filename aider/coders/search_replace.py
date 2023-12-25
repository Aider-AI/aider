#!/usr/bin/env python

import sys
from pathlib import Path

import git
from diff_match_patch import diff_match_patch
from tqdm import tqdm

from aider.dump import dump
from aider.utils import GitTemporaryDirectory


class RelativeIndenter:
    """Rewrites text files to have relative indentation, which involves
    reformatting the leading white space on lines.  This format makes
    it easier to search and apply edits to pairs of code blocks which
    may differ significantly in their overall level of indentation.

    It removes leading white space which is shared with the preceding
    line.

    Original:
    ```
            Foo # indented 8
                Bar # indented 4 more than the previous line
                Baz # same indent as the previous line
                Fob # same indent as the previous line
    ```

    Becomes:
    ```
            Foo # indented 8
        Bar # indented 4 more than the previous line
    Baz # same indent as the previous line
    Fob # same indent as the previous line
    ```

    If the current line is *less* indented then the previous line,
    uses a unicode character to indicate outdenting.

    Original
    ```
            Foo
                Bar
                Baz
            Fob # indented 4 less than the previous line
    ```

    Becomes:
    ```
            Foo
        Bar
    Baz
    ←←←←Fob # indented 4 less than the previous line
    ```

    This is a similar original to the last one, but every line has
    been uniformly outdented:
    ```
    Foo
        Bar
        Baz
    Fob # indented 4 less than the previous line
    ```

    It becomes this result, which is very similar to the previous
    result.  Only the white space on the first line differs.  From the
    word Foo onwards, it is identical to the previous result.
    ```
    Foo
        Bar
    Baz
    ←←←←Fob # indented 4 less than the previous line
    ```

    """

    def __init__(self, texts):
        """
        Based on the texts, choose a unicode character that isn't in any of them.
        """

        chars = set()
        for text in texts:
            chars.update(text)

        ARROW = "←"
        if ARROW not in chars:
            self.marker = ARROW
        else:
            self.marker = self.select_unique_marker(chars)

    def select_unique_marker(self, chars):
        for codepoint in range(0x10FFFF, 0x10000, -1):
            marker = chr(codepoint)
            if marker not in chars:
                return marker

        raise ValueError("Could not find a unique marker")

    def make_relative(self, text):
        """
        Transform text to use relative indents.
        """

        if self.marker in text:
            raise ValueError("Text already contains the outdent marker: {self.marker}")

        lines = text.splitlines(keepends=True)

        output = []
        prev_indent = ""
        for line in lines:
            line_without_end = line.rstrip("\n\r")

            len_indent = len(line_without_end) - len(line_without_end.lstrip())
            indent = line[:len_indent]
            change = len_indent - len(prev_indent)
            if change > 0:
                cur_indent = indent[-change:]
            elif change < 0:
                cur_indent = self.marker * -change
            else:
                cur_indent = ""

            out_line = cur_indent + "\n" + line[len_indent:]
            # dump(len_indent, change, out_line)
            # print(out_line)
            output.append(out_line)
            prev_indent = indent

        res = "".join(output)
        return res

    def make_absolute(self, text):
        """
        Transform text from relative back to absolute indents.
        """
        lines = text.splitlines(keepends=True)

        output = []
        prev_indent = ""
        for i in range(0, len(lines), 2):
            dent = lines[i].rstrip("\r\n")
            non_indent = lines[i + 1]

            if dent.startswith(self.marker):
                len_outdent = len(dent)
                cur_indent = prev_indent[:-len_outdent]
            else:
                cur_indent = prev_indent + dent

            if not non_indent.rstrip("\r\n"):
                out_line = non_indent  # don't indent a blank line
            else:
                out_line = cur_indent + non_indent

            output.append(out_line)
            prev_indent = cur_indent

        res = "".join(output)
        if self.marker in res:
            # dump(res)
            raise ValueError("Error transforming text back to absolute indents")

        return res


# The patches are created to change S->R.
# So all the patch offsets are relative to S.
# But O has a lot more content. So all the offsets are very wrong.
#
# But patch_apply() seems to imply that once patch N is located,
# then it adjusts the offset of the next patch.
#
# This is great, because once we sync up after a big gap the nearby
# patches are close to being located right.
# Except when indentation has been changed by GPT.
#
# It would help to use the diff trick to build map_S_offset_to_O_offset().
# Then update all the S offsets in the S->R patches to be O offsets.
# Do we also need to update the R offsets?
#
# What if this gets funky/wrong?
#


def map_patches(texts, patches, debug):
    search_text, replace_text, original_text = texts

    dmp = diff_match_patch()
    dmp.Diff_Timeout = 5

    diff_s_o = dmp.diff_main(search_text, original_text)
    # diff_r_s = dmp.diff_main(replace_text, search_text)

    # dmp.diff_cleanupSemantic(diff_s_o)
    # dmp.diff_cleanupEfficiency(diff_s_o)

    if debug:
        html = dmp.diff_prettyHtml(diff_s_o)
        Path("tmp.html").write_text(html)

        dump(len(search_text))
        dump(len(original_text))

    for patch in patches:
        start1 = patch.start1
        start2 = patch.start2

        patch.start1 = dmp.diff_xIndex(diff_s_o, start1)
        patch.start2 = dmp.diff_xIndex(diff_s_o, start2)

        if debug:
            print()
            print(start1, repr(search_text[start1 : start1 + 50]))
            print(patch.start1, repr(original_text[patch.start1 : patch.start1 + 50]))
            print(patch.diffs)
            print()

    return patches


example = """Left
Left
    4 in
    4 in
        8 in
    4 in
Left
"""

"""
ri = RelativeIndenter([example])
dump(example)

rel_example = ri.make_relative(example)
dump(repr(rel_example))

abs_example = ri.make_absolute(rel_example)
dump(abs_example)


sys.exit()
"""


def relative_indent(texts):
    ri = RelativeIndenter(texts)
    texts = list(map(ri.make_relative, texts))

    return ri, texts


line_padding = 100


def line_pad(text):
    padding = "\n" * line_padding
    return padding + text + padding


def line_unpad(text):
    if set(text[:line_padding] + text[-line_padding:]) != set("\n"):
        return
    return text[line_padding:-line_padding]


def dmp_apply(texts, remap=True):
    debug = False
    # debug = True

    search_text, replace_text, original_text = texts

    dmp = diff_match_patch()
    dmp.Diff_Timeout = 5
    # dmp.Diff_EditCost = 16

    if remap:
        dmp.Match_Threshold = 0.95
        dmp.Match_Distance = 500
        dmp.Match_MaxBits = 128
        dmp.Patch_Margin = 32
    else:
        dmp.Match_Threshold = 0.5
        dmp.Match_Distance = 100_000
        dmp.Match_MaxBits = 32
        dmp.Patch_Margin = 8

    diff = dmp.diff_main(search_text, replace_text, None)
    dmp.diff_cleanupSemantic(diff)
    dmp.diff_cleanupEfficiency(diff)

    patches = dmp.patch_make(search_text, diff)

    if debug:
        html = dmp.diff_prettyHtml(diff)
        Path("tmp.search_replace_diff.html").write_text(html)

        for d in diff:
            print(d[0], repr(d[1]))

        for patch in patches:
            start1 = patch.start1
            print()
            print(start1, repr(search_text[start1 : start1 + 10]))
            print(start1, repr(replace_text[start1 : start1 + 10]))
            print(patch.diffs)

        # dump(original_text)
        # dump(search_text)

    if remap:
        patches = map_patches(texts, patches, debug)

    patches_text = dmp.patch_toText(patches)

    new_text, success = dmp.patch_apply(patches, original_text)

    all_success = False not in success

    if debug:
        # dump(new_text)
        print(patches_text)

        # print(new_text)
        dump(success)
        dump(all_success)

        # print(new_text)

    if not all_success:
        return

    return new_text


def lines_to_chars(lines, mapping):
    new_text = []
    for char in lines:
        new_text.append(mapping[ord(char)])

    new_text = "".join(new_text)
    return new_text


def dmp_lines_apply(texts, remap=True):
    debug = False
    # debug = True

    for t in texts:
        assert t.endswith("\n"), t

    search_text, replace_text, original_text = texts

    dmp = diff_match_patch()
    dmp.Diff_Timeout = 5
    # dmp.Diff_EditCost = 16

    dmp.Match_Threshold = 0.1
    dmp.Match_Distance = 100_000
    dmp.Match_MaxBits = 32
    dmp.Patch_Margin = 1

    all_text = search_text + replace_text + original_text
    all_lines, _, mapping = dmp.diff_linesToChars(all_text, "")
    assert len(all_lines) == len(all_text.splitlines())

    search_num = len(search_text.splitlines())
    replace_num = len(replace_text.splitlines())
    original_num = len(original_text.splitlines())

    search_lines = all_lines[:search_num]
    replace_lines = all_lines[search_num : search_num + replace_num]
    original_lines = all_lines[search_num + replace_num :]

    assert len(search_lines) == search_num
    assert len(replace_lines) == replace_num
    assert len(original_lines) == original_num

    diff_lines = dmp.diff_main(search_lines, replace_lines, None)
    dmp.diff_cleanupSemantic(diff_lines)
    dmp.diff_cleanupEfficiency(diff_lines)

    patches = dmp.patch_make(search_lines, diff_lines)

    if debug:
        diff = list(diff_lines)
        dmp.diff_charsToLines(diff, mapping)
        # dump(diff)
        html = dmp.diff_prettyHtml(diff)
        Path("tmp.search_replace_diff.html").write_text(html)

        for d in diff:
            print(d[0], repr(d[1]))

    new_lines, success = dmp.patch_apply(patches, original_lines)
    new_text = lines_to_chars(new_lines, mapping)

    all_success = False not in success

    if debug:
        # print(new_text)
        dump(success)
        dump(all_success)

        # print(new_text)

    if not all_success:
        return

    return new_text


def diff_lines(search_text, replace_text):
    dmp = diff_match_patch()
    dmp.Diff_Timeout = 5
    # dmp.Diff_EditCost = 16
    search_lines, replace_lines, mapping = dmp.diff_linesToChars(search_text, replace_text)

    diff_lines = dmp.diff_main(search_lines, replace_lines, None)
    dmp.diff_cleanupSemantic(diff_lines)
    dmp.diff_cleanupEfficiency(diff_lines)

    diff = list(diff_lines)
    dmp.diff_charsToLines(diff, mapping)
    # dump(diff)

    udiff = []
    for d, lines in diff:
        if d < 0:
            d = "-"
        elif d > 0:
            d = "+"
        else:
            d = " "
        for line in lines.splitlines(keepends=True):
            udiff.append(d + line)

    return udiff


def search_and_replace(texts):
    search_text, replace_text, original_text = texts

    num = original_text.count(search_text)
    # if num > 1:
    #    raise SearchTextNotUnique()
    if num == 0:
        return

    new_text = original_text.replace(search_text, replace_text)

    return new_text


def git_cherry_pick_osr_onto_o(texts):
    search_text, replace_text, original_text = texts

    with GitTemporaryDirectory() as dname:
        repo = git.Repo(dname)

        fname = Path(dname) / "file.txt"

        # Make O->S->R
        fname.write_text(original_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "original")
        original_hash = repo.head.commit.hexsha

        fname.write_text(search_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "search")

        fname.write_text(replace_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "replace")
        replace_hash = repo.head.commit.hexsha

        # go back to O
        repo.git.checkout(original_hash)

        # cherry pick R onto original
        try:
            repo.git.cherry_pick(replace_hash, "--minimal")
        except git.exc.GitCommandError:
            # merge conflicts!
            return

        new_text = fname.read_text()
        return new_text


def git_cherry_pick_sr_onto_so(texts):
    search_text, replace_text, original_text = texts

    with GitTemporaryDirectory() as dname:
        repo = git.Repo(dname)

        fname = Path(dname) / "file.txt"

        fname.write_text(search_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "search")
        search_hash = repo.head.commit.hexsha

        # make search->replace
        fname.write_text(replace_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "replace")
        replace_hash = repo.head.commit.hexsha

        # go back to search,
        repo.git.checkout(search_hash)

        # make search->original
        fname.write_text(original_text)
        repo.git.add(str(fname))
        repo.git.commit("-m", "original")

        # cherry pick replace onto original
        try:
            repo.git.cherry_pick(replace_hash, "--minimal")
        except git.exc.GitCommandError:
            # merge conflicts!
            return

        new_text = fname.read_text()

        return new_text


class SearchTextNotUnique(ValueError):
    pass


all_preprocs = [
    # (strip_blank_lines, relative_indent, reverse_lines)
    (False, False, False),
    (True, False, False),
    (False, True, False),
    (True, True, False),
    # (False, False, True),
    # (True, False, True),
    # (False, True, True),
    # (True, True, True),
]

always_relative_indent = [
    (False, True, False),
    (True, True, False),
    # (False, True, True),
    # (True, True, True),
]

editblock_strategies = [
    (search_and_replace, all_preprocs),
    (git_cherry_pick_osr_onto_o, all_preprocs),
    (dmp_lines_apply, all_preprocs),
]

never_relative = [
    (False, False),
    (True, False),
]

udiff_strategies = [
    (search_and_replace, all_preprocs),
    (git_cherry_pick_osr_onto_o, all_preprocs),
    (dmp_lines_apply, all_preprocs),
]


def flexible_search_and_replace(texts, strategies):
    """Try a series of search/replace methods, starting from the most
    literal interpretation of search_text. If needed, progress to more
    flexible methods, which can accommodate divergence between
    search_text and original_text and yet still achieve the desired
    edits.
    """

    for strategy, preprocs in strategies:
        for preproc in preprocs:
            res = try_strategy(texts, strategy, preproc)
            if res:
                return res


def reverse_lines(text):
    lines = text.splitlines(keepends=True)
    lines.reverse()
    return "".join(lines)


def try_strategy(texts, strategy, preproc):
    preproc_strip_blank_lines, preproc_relative_indent, preproc_reverse = preproc
    ri = None

    if preproc_strip_blank_lines:
        texts = strip_blank_lines(texts)
    if preproc_relative_indent:
        ri, texts = relative_indent(texts)
    if preproc_reverse:
        texts = list(map(reverse_lines, texts))

    res = strategy(texts)

    if res and preproc_reverse:
        res = reverse_lines(res)

    if res and preproc_relative_indent:
        try:
            res = ri.make_absolute(res)
        except ValueError:
            return

    return res


def strip_blank_lines(texts):
    # strip leading and trailing blank lines
    texts = [text.strip("\n") + "\n" for text in texts]
    return texts


def read_text(fname):
    text = Path(fname).read_text()
    return text


def proc(dname):
    dname = Path(dname)

    try:
        search_text = read_text(dname / "search")
        replace_text = read_text(dname / "replace")
        original_text = read_text(dname / "original")
    except FileNotFoundError:
        return

    ####

    texts = search_text, replace_text, original_text

    strategies = [
        # (search_and_replace, all_preprocs),
        # (git_cherry_pick_osr_onto_o, all_preprocs),
        # (git_cherry_pick_sr_onto_so, all_preprocs),
        # (dmp_apply, all_preprocs),
        (dmp_lines_apply, all_preprocs),
    ]

    _strategies = editblock_strategies  # noqa: F841

    short_names = dict(
        search_and_replace="sr",
        git_cherry_pick_osr_onto_o="cp_o",
        git_cherry_pick_sr_onto_so="cp_so",
        dmp_apply="dmp",
        dmp_lines_apply="dmpl",
    )

    patched = dict()
    for strategy, preprocs in strategies:
        for preproc in preprocs:
            method = strategy.__name__
            method = short_names[method]

            strip_blank, rel_indent, rev_lines = preproc
            if strip_blank or rel_indent:
                method += "_"
            if strip_blank:
                method += "s"
            if rel_indent:
                method += "i"
            if rev_lines:
                method += "r"

            res = try_strategy(texts, strategy, preproc)
            patched[method] = res

    results = []
    for method, res in patched.items():
        out_fname = dname / f"original.{method}"
        if out_fname.exists():
            out_fname.unlink()

        if res:
            out_fname.write_text(res)

            correct = (dname / "correct").read_text()
            if res == correct:
                res = "pass"
            else:
                res = "WRONG"
        else:
            res = "fail"

        results.append((method, res))

    return results


def colorize_result(result):
    colors = {
        "pass": "\033[102;30mpass\033[0m",  # Green background, black text
        "WRONG": "\033[101;30mWRONG\033[0m",  # Red background, black text
        "fail": "\033[103;30mfail\033[0m",  # Yellow background, black text
    }
    return colors.get(result, result)  # Default to original result if not found


def main(dnames):
    all_results = []
    for dname in tqdm(dnames):
        dname = Path(dname)
        results = proc(dname)
        for method, res in results:
            all_results.append((dname, method, res))
            # print(dname, method, colorize_result(res))

    # Create a 2D table with directories along the right and methods along the top
    # Collect all unique methods and directories
    methods = []
    for _, method, _ in all_results:
        if method not in methods:
            methods.append(method)

    directories = dnames

    # Sort directories by decreasing number of 'pass' results
    pass_counts = {
        dname: sum(
            res == "pass" for dname_result, _, res in all_results if str(dname) == str(dname_result)
        )
        for dname in directories
    }
    directories.sort(key=lambda dname: pass_counts[dname], reverse=True)

    # Create a results matrix
    results_matrix = {dname: {method: "" for method in methods} for dname in directories}

    # Populate the results matrix
    for dname, method, res in all_results:
        results_matrix[str(dname)][method] = res

    # Print the 2D table
    # Print the header
    print("{:<20}".format("Directory"), end="")
    for method in methods:
        print("{:<9}".format(method), end="")
    print()

    # Print the rows with colorized results
    for dname in directories:
        print("{:<20}".format(Path(dname).name), end="")
        for method in methods:
            res = results_matrix[dname][method]
            colorized_res = colorize_result(res)
            res_l = 9 + len(colorized_res) - len(res)
            fmt = "{:<" + str(res_l) + "}"
            print(fmt.format(colorized_res), end="")
        print()


if __name__ == "__main__":
    status = main(sys.argv[1:])
    sys.exit(status)
