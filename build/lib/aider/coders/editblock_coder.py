import math
import re
from difflib import SequenceMatcher
from pathlib import Path

from .base_coder import Coder
from .editblock_prompts import EditBlockPrompts


class EditBlockCoder(Coder):
    def __init__(self, *args, **kwargs):
        self.gpt_prompts = EditBlockPrompts()
        super().__init__(*args, **kwargs)

    def update_files(self):
        content = self.partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        edits = list(find_original_update_blocks(content))

        edited = set()
        for path, original, updated in edits:
            full_path = self.allowed_to_edit(path)
            if not full_path:
                continue
            content = self.io.read_text(full_path)
            content = do_replace(full_path, content, original, updated)
            if content:
                self.io.write_text(full_path, content)
                edited.add(path)
                continue
            raise ValueError(f"""InvalidEditBlock: edit failed!

{path} does not contain the *exact sequence* of ORIGINAL lines you specified.
Try again.
DO NOT skip blank lines, comments, docstrings, etc!
The ORIGINAL block needs to be EXACTLY the same as the lines in {path} with nothing missing!

{path} does not contain these {len(original.splitlines())} exact lines in a row:
```
{original}```
""")

        return edited


def try_dotdotdots(whole, part, replace):
    """
    See if the edit block has ... lines.
    If not, return none.

    If yes, try and do a perfect edit with the ... chunks.
    If there's a mismatch or otherwise imperfect edit, raise ValueError.

    If perfect edit succeeds, return the updated whole.
    """

    dots_re = re.compile(r"(^\s*\.\.\.\n)", re.MULTILINE | re.DOTALL)

    part_pieces = re.split(dots_re, part)
    replace_pieces = re.split(dots_re, replace)

    if len(part_pieces) != len(replace_pieces):
        raise ValueError("Unpaired ... in edit block")

    if len(part_pieces) == 1:
        # no dots in this edit block, just return None
        return

    # Compare odd strings in part_pieces and replace_pieces
    all_dots_match = all(part_pieces[i] == replace_pieces[i] for i in range(1, len(part_pieces), 2))

    if not all_dots_match:
        raise ValueError("Unmatched ... in edit block")

    part_pieces = [part_pieces[i] for i in range(0, len(part_pieces), 2)]
    replace_pieces = [replace_pieces[i] for i in range(0, len(replace_pieces), 2)]

    pairs = zip(part_pieces, replace_pieces)
    for part, replace in pairs:
        if not part and not replace:
            continue

        if not part and replace:
            if not whole.endswith("\n"):
                whole += "\n"
            whole += replace
            continue

        if whole.count(part) != 1:
            raise ValueError(
                "No perfect matching chunk in edit block with ... or part appears more than once"
            )

        whole = whole.replace(part, replace, 1)

    return whole


def replace_part_with_missing_leading_whitespace(whole, part, replace):
    whole_lines = whole.splitlines()
    part_lines = part.splitlines()
    replace_lines = replace.splitlines()

    # If all lines in the part start with whitespace, then honor it.
    # But GPT often outdents the part and replace blocks completely,
    # thereby discarding the actual leading whitespace in the file.
    if all((not pline or pline[0].isspace()) for pline in part_lines):
        return

    for i in range(len(whole_lines) - len(part_lines) + 1):
        leading_whitespace = ""
        for j, c in enumerate(whole_lines[i]):
            if c == part_lines[0][0]:
                leading_whitespace = whole_lines[i][:j]
                break

        if not leading_whitespace or not all(c.isspace() for c in leading_whitespace):
            continue

        matched = all(
            whole_lines[i + k].startswith(leading_whitespace + part_lines[k])
            for k in range(len(part_lines))
        )

        if matched:
            replace_lines = [
                leading_whitespace + rline if rline else rline for rline in replace_lines
            ]
            whole_lines = whole_lines[:i] + replace_lines + whole_lines[i + len(part_lines) :]
            return "\n".join(whole_lines) + "\n"

    return None


def replace_most_similar_chunk(whole, part, replace):
    res = replace_part_with_missing_leading_whitespace(whole, part, replace)
    if res:
        return res

    if part in whole:
        return whole.replace(part, replace)

    try:
        res = try_dotdotdots(whole, part, replace)
    except ValueError:
        return

    if res:
        return res

    similarity_thresh = 0.8

    max_similarity = 0
    most_similar_chunk_start = -1
    most_similar_chunk_end = -1

    whole_lines = whole.splitlines()
    part_lines = part.splitlines()

    scale = 0.1
    min_len = math.floor(len(part_lines) * (1 - scale))
    max_len = math.ceil(len(part_lines) * (1 + scale))

    for length in range(min_len, max_len):
        for i in range(len(whole_lines) - length + 1):
            chunk = whole_lines[i : i + length]
            chunk = "\n".join(chunk)

            similarity = SequenceMatcher(None, chunk, part).ratio()

            if similarity > max_similarity and similarity:
                max_similarity = similarity
                most_similar_chunk_start = i
                most_similar_chunk_end = i + length

    if max_similarity < similarity_thresh:
        return

    replace_lines = replace.splitlines()

    modified_whole = (
        whole_lines[:most_similar_chunk_start]
        + replace_lines
        + whole_lines[most_similar_chunk_end:]
    )
    modified_whole = "\n".join(modified_whole)

    if whole.endswith("\n"):
        modified_whole += "\n"

    return modified_whole


def strip_quoted_wrapping(res, fname=None, fence=None):
    """
    Given an input string which may have extra "wrapping" around it, remove the wrapping.
    For example:

    filename.ext
    ```
    We just want this content
    Not the filename and triple quotes
    ```
    """
    if not res:
        return res

    if not fence:
        fence = ("```", "```")

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res


def do_replace(fname, content, before_text, after_text, fence=None):
    before_text = strip_quoted_wrapping(before_text, fname, fence)
    after_text = strip_quoted_wrapping(after_text, fname, fence)
    fname = Path(fname)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()
        content = ""

    if content is None:
        return

    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
    else:
        new_content = replace_most_similar_chunk(content, before_text, after_text)

    return new_content


ORIGINAL = "<<<<<<< ORIGINAL"
DIVIDER = "======="
UPDATED = ">>>>>>> UPDATED"

separators = "|".join([ORIGINAL, DIVIDER, UPDATED])

split_re = re.compile(r"^((?:" + separators + r")[ ]*\n)", re.MULTILINE | re.DOTALL)


def find_original_update_blocks(content):
    # make sure we end with a newline, otherwise the regex will miss <<UPD on the last line
    if not content.endswith("\n"):
        content = content + "\n"

    pieces = re.split(split_re, content)

    pieces.reverse()
    processed = []

    # Keep using the same filename in cases where GPT produces an edit block
    # without a filename.
    current_filename = None
    try:
        while pieces:
            cur = pieces.pop()

            if cur in (DIVIDER, UPDATED):
                processed.append(cur)
                raise ValueError(f"Unexpected {cur}")

            if cur.strip() != ORIGINAL:
                processed.append(cur)
                continue

            processed.append(cur)  # original_marker

            filename = processed[-2].splitlines()[-1].strip()
            try:
                if not len(filename) or "`" in filename:
                    filename = processed[-2].splitlines()[-2].strip()
                if not len(filename) or "`" in filename:
                    if current_filename:
                        filename = current_filename
                    else:
                        raise ValueError(
                            f"Bad/missing filename. It should go right above {ORIGINAL}"
                        )
            except IndexError:
                if current_filename:
                    filename = current_filename
                else:
                    raise ValueError(f"Bad/missing filename. It should go right above {ORIGINAL}")

            current_filename = filename

            original_text = pieces.pop()
            processed.append(original_text)

            divider_marker = pieces.pop()
            processed.append(divider_marker)
            if divider_marker.strip() != DIVIDER:
                raise ValueError(f"Expected {DIVIDER}")

            updated_text = pieces.pop()
            processed.append(updated_text)

            updated_marker = pieces.pop()
            processed.append(updated_marker)
            if updated_marker.strip() != UPDATED:
                raise ValueError(f"Expected {UPDATED}")

            yield filename, original_text, updated_text
    except ValueError as e:
        processed = "".join(processed)
        err = e.args[0]
        raise ValueError(f"{processed}\n^^^ {err}")
    except IndexError:
        processed = "".join(processed)
        raise ValueError(f"{processed}\n^^^ Incomplete ORIGINAL/UPDATED block.")
    except Exception:
        processed = "".join(processed)
        raise ValueError(f"{processed}\n^^^ Error parsing ORIGINAL/UPDATED block.")


if __name__ == "__main__":
    edit = """
Here's the change:

```text
foo.txt
<<<<<<< ORIGINAL
Two
=======
Tooooo
>>>>>>> UPDATED
```

Hope you like it!
"""
    print(list(find_original_update_blocks(edit)))
