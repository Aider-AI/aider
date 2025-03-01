import difflib
import math
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from aider import utils

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .linediff_prompts import LineDiffPrompts
from aider.utils import is_image_file

DEFAULT_FENCE = ("`" * 3, "`" * 3)
HEAD = r"^<{5,9} REMOVE\s*$"
DIVIDER = r"^={5,9}\s*$"
UPDATED = r"^>{5,9} INSERT\s*$"

HEAD_ERR = "<<<<<<< REMOVE"
DIVIDER_ERR = "======="
UPDATED_ERR = ">>>>>>> INSERT"

separators = "|".join([HEAD, DIVIDER, UPDATED])

split_re = re.compile(r"^((?:" + separators + r")[ ]*\n)", re.MULTILINE | re.DOTALL)

missing_filename_err = (
    "Bad/missing filename. The filename must be alone on the line before the opening fence"
    " {fence[0]}"
)

# print green
def printg(text):
    print(f"\033[92m{text}\033[0m")

# print blue
def printb(text):
    print(f"\033[94m{text}\033[0m")

# print yellow, warning
def printw(text):
    print(f"\033[33m{text}\033[0m")

# print red
def printr(text):
    print(f"\033[91m{text}\033[0m")

class LineDiffCoder(Coder):
    """A coder that uses remove/insert blocks for code modifications."""

    edit_format = "ldiff"
    gpt_prompts = LineDiffPrompts()
    source_fence = ("<source>","</source>")
    fence = ("<editblock>","</editblock>")

    # def choose_fence(self):
        # self.verbose = True
        # return

    def format_messages(self):
        new_done = []
        for message in self.done_messages:
            role = message["role"]
            content = message["content"]
            lines = content.splitlines(keepends=True)
            filtered_lines = [line for line in lines if "<source>" not in line and "</source>" not in line]
            new_content = "".join(filtered_lines)
            new_done.append(dict(role=role, content=new_content))

        self.done_messages = new_done

        chunks = self.format_chat_chunks()
        if self.add_cache_headers:
            chunks.add_cache_control_headers()

        return chunks

    def get_files_content(self, fnames=None):
        if not fnames:
            fnames = self.abs_fnames

        prompt = ""
        for fname, content in self.get_abs_fnames_content():
            if not is_image_file(fname):
                relative_fname = self.get_rel_fname(fname)
                prompt += "\n"
                prompt += relative_fname
                prompt += f"\n{self.source_fence[0]}\n"

                content, lines = prep(content)
                lines_len = len(lines)
                digits = math.ceil(math.log10(lines_len + 1))
                lines = [f"{i+1:0{digits}}{line_separator}{line}" for i, line in enumerate(lines)]
                prompt += "".join(lines)

                prompt += f"{self.source_fence[1]}\n"

        return prompt

    def get_file_content_numbered(self, fname):
        content = self.io.read_text(fname)

        if content:
            res = ""
            content, lines = prep(content)
            lines_len = len(lines)
            digits = math.ceil(math.log10(lines_len + 1))
            lines = [f"{i+1:0{digits}}{line_separator}{line}" for i, line in enumerate(lines)]
            res += "".join(lines)

            return res

    def get_edits(self):
        content = self.partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        edits = list(
            self.find_original_update_blocks(
                content,
                self.fence,
                self.get_inchat_relative_files(),
            )
        )

        self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
        edits = [edit for edit in edits if edit[0] is not None]

        return edits

    def apply_edits(self, edits):
        failed = []
        passed = []

        content_maps = {}
        editblocks = {}
        for edit in edits:
            path, removed, replaced = edit

            full_path = self.abs_root_path(path)
            content = self.get_file_content_numbered(full_path)

            content_map = content_maps.get(full_path)
            if content_map is None:
                # print("original content:")
                # printb(str(content))

                if content is None:
                    content_map = ContentMap()
                else:
                    content_map = ContentMap(content)

            removed = strip_quoted_wrapping(removed, full_path, self.fence)
            replaced = strip_quoted_wrapping(replaced, full_path, self.fence)
            removed_map = ContentMap(removed)
            replaced_map = ContentMap(replaced, fallback=True)

            editblock = EditBlock(content_map, removed_map, replaced_map)

            if content_map.applied(editblock):
                # printw("Block already applied, skipping")
                # printw(editblock.as_content(numbered=True))
                passed.append(edit)
            else:
                success, new_content_map, new_editblock = do_replace(full_path, content_map, editblock)

                if success:
                    content_map = new_content_map
                    passed.append(edit)
                else:
                    editblock = new_editblock
                    failed.append(edit)

            content_maps[full_path] = content_map
            editblocks[full_path] = editblock

        for full_path, content_map in content_maps.items():
            new_content = content_map.as_content(apply=True, numbered=False)

            # print("new content:")
            # printw(new_content)

            self.io.write_text(full_path, new_content)

        if not failed:
            return

        blocks = "block" if len(failed) == 1 else "blocks"

        res = f"# {len(failed)} *edit{blocks}* failed to match!\n"
        for edit in failed:
            path, original, updated = edit

            full_path = self.abs_root_path(path)
            content = self.io.read_text(full_path)
            editblock = editblocks[full_path]

            res += f"""## EditblockNoExactMatch: This *editblock* failed to exactly match lines in {path}
{editblock.as_content(numbered=True, mismatch=True)}
"""
#             did_you_mean = find_similar_lines(original, content)
#             if did_you_mean:
#                 res += f"""Did you mean to match some of these actual lines from {path}?
#
# {self.fence[0]}
# {did_you_mean}
# {self.fence[1]}
#
# """

            if updated in content and updated:
                res += f"""Are you sure you need this *editblock*?
The INSERT lines are already in {path}!

"""
        # res += (
        #     "The REMOVE section must exactly match an existing block of lines including all white"
        #     " space, comments, indentation, docstrings, etc\n"
        # )
        if passed:
            pblocks = "block" if len(passed) == 1 else "blocks"
            res += f"""
# The other {len(passed)} *edit{pblocks}* were applied successfully."""

        res+= f"""
I won't try to re-apply them. As they broke the *editblock* format rules by not matching the latest source.
Reply with new *editblocks* based off the latest code version.
"""
        raise ValueError(res)

    def find_original_update_blocks(self, content, fence=DEFAULT_FENCE, valid_fnames=None):
        lines = content.splitlines(keepends=True)
        i = 0
        current_filename = None

        head_pattern = re.compile(HEAD)
        divider_pattern = re.compile(DIVIDER)
        updated_pattern = re.compile(UPDATED)

        def starts_remove(line):
            return head_pattern.match(line.strip())
        def ends_remove(line):
            return divider_pattern.match(line.strip())
        def ends_insert(line):
            return updated_pattern.match(line.strip()) or fence[1] in line

        if HEAD_ERR in content or UPDATED_ERR in content or DIVIDER_ERR in content:
            while i < len(lines):
                line = lines[i]

                # Check for shell code blocks
                shell_starts = [
                    "```bash",
                    "```sh",
                    "```shell",
                    "```cmd",
                    "```batch",
                    "```powershell",
                    "```ps1",
                    "```zsh",
                    "```fish",
                    "```ksh",
                    "```csh",
                    "```tcsh",
                ]
                next_is_editblock = i + 1 < len(lines) and head_pattern.match(lines[i + 1].strip())

                if any(line.strip().startswith(start) for start in shell_starts) and not next_is_editblock:
                    shell_content = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith("```"):
                        shell_content.append(lines[i])
                        i += 1
                    if i < len(lines) and lines[i].strip().startswith("```"):
                        i += 1  # Skip the closing ```

                    yield None, "".join(shell_content)
                    continue

                # Check for REMOVE/INSERT blocks
                if starts_remove(line):
                    try:
                        filename = find_filename(lines[max(0, i - 3) : i], fence, valid_fnames)

                        if not filename:
                            # if next line after HEAD exists and is DIVIDER, it may be a new file
                            if i + 1 < len(lines) and ends_remove(lines[i + 1]):
                                filename = find_filename(lines[max(0, i - 3) : i], fence, None)

                        if not filename:
                            if current_filename:
                                filename = current_filename
                            else:
                                raise ValueError(missing_filename_err.format(fence=fence))

                        current_filename = filename

                        original_text = []
                        i += 1
                        while i < len(lines) and not ends_remove(lines[i]):
                            original_text.append(lines[i])
                            i += 1

                        if i >= len(lines) or not ends_remove(lines[i]):
                            raise ValueError(f"Expected `{DIVIDER_ERR}`")

                        updated_text = []
                        i += 1

                        while i < len(lines) and not ends_insert(lines[i]):
                            updated_text.append(lines[i])
                            i += 1

                        if i >= len(lines) or not ends_insert(lines[i]):
                            raise ValueError(f"Expected `{UPDATED_ERR}`")

                        yield filename, "".join(original_text), "".join(updated_text)

                    except ValueError as e:
                        processed = "".join(lines[: i + 1])
                        err = e.args[0]
                        raise ValueError(f"{processed}\n^^^ {err}")


                i += 1
        else:
            while i < len(lines):
                line = lines[i]

                next_is_numbered_line = False
                if i + 1 < len(lines):
                    line_nr, line_cont = parse_line(lines[i+1].strip())
                    next_is_numbered_line = line_nr is not None


                if line.strip().startswith(fence[0]) and i > 0 and next_is_numbered_line:
                    prev_line = lines[i - 1].strip()
                    if strip_filename(prev_line, fence):
                        fenced_content = []
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith(fence[1]):
                            fenced_content.append(lines[i])
                            i += 1
                        if i < len(lines) and lines[i].strip().startswith(fence[1]):
                            i += 1  # Skip the closing fence

                        filename = strip_filename(prev_line, fence)
                        full_path = self.abs_root_path(filename)
                        # printr("turned fenced block into update block")
                        # printr("filename: "+filename)
                        original_content = self.get_file_content_numbered(full_path)
                        yield filename, original_content, "".join(fenced_content)
                        continue
                i += 1
class EditBlock:
    def __init__(self, source_map, remove_map, insert_map):
        self._source_map = source_map
        self._remove_map = remove_map
        self._insert_map = insert_map
        self._mismatch = None

    @property
    def mismatch(self):
        return self._mismatch

    @mismatch.setter
    def mismatch(self, value):
        if not isinstance(value, (int, type(None))):
            raise TypeError("mismatch must be an integer or None")
        self._mismatch = value

    def __len__(self):
        return len(self._remove_map)

    @property
    def source_map(self):
        return self._source_map

    @property
    def remove_map(self):
        return self._remove_map

    @property
    def insert_map(self):
        return self._insert_map

    def as_content(self, numbered=False, mismatch=False):
        if mismatch:
            if self._mismatch is not None:
                removed = self.remove_map[self._mismatch]
                source = self.source_map[self._mismatch]

                if numbered:
                    removed = self.remove_map.as_numbered_line(removed, self._mismatch)
                    source = self.source_map.as_numbered_line(source, self._mismatch)

                return f"{HEAD_ERR}\n{removed}{DIVIDER_ERR}\n{source}>>>>>>> SOURCE\n"
            else:
                return "ALL LINES MATCHED"
        else:
            removed = self._remove_map.as_content(apply=False, numbered=numbered)
            inserted = self._insert_map.as_content(apply=False, padded=numbered)

            return f"{HEAD_ERR}\n{removed}{DIVIDER_ERR}\n{inserted}{UPDATED_ERR}\n"

class ContentMap:
    def __init__(self, content=None, fallback=False):
        self._map = {}
        self._len = 0
        self._digits = 0
        self._applied_edits = []
        if content:
            _, content_lines = prep(content)
            res = {}

            for line in content_lines:
                line_number, line_content = parse_line(line)
                if line_number and line_content:
                    res[line_number] = line_content

            # INSERT lines are returned without line numbers.
            if not res and fallback:
                for line_number, line in enumerate(content_lines):
                    _, line_content = parse_line(line)
                    res[line_number + 1] = line_content

            self._map = res
            self._len = len(self._map)
            self._digits = math.ceil(math.log10(self._len + 1))

    def apply(self, editblock):
        self._applied_edits.append(editblock)

    def applied(self, editblock):
        removed_content = editblock.remove_map.as_content(numbered=True)
        inserted_content = editblock.insert_map.as_content(numbered=False, padded=False)

        for applied in self._applied_edits:
            removed_content_applied = applied.remove_map.as_content(numbered=True)
            inserted_content_applied = applied.insert_map.as_content(numbered=False, padded=False)

            if removed_content in removed_content_applied:
                if inserted_content in inserted_content_applied:
                    return True
            if removed_content_applied in removed_content:
                if inserted_content in inserted_content_applied:
                    return True
            return False

        return False

    def as_numbered_line(self, line, number):
        return f"{number:0{self._digits}}{line_separator}{line}"

    def as_padded_line(self, line):
        return f"{' ' * self._digits}{line_separator}{line}"

    def do_apply(self):
        res = {}

        for editblock in self._applied_edits:
            if len(editblock.remove_map) == 0:
                insert_idx = max(self._map.keys()) + 1
                for offset, line in enumerate(editblock.insert_map.values()):
                    self._map[insert_idx + offset] = line
            else:
                insert_idx = min(editblock.remove_map.keys())

                for num in editblock.remove_map.keys():
                    self._map[num] = []
                self._map[insert_idx] = list(editblock.insert_map.values())

        i = 1
        for value in self._map.values():
            if isinstance(value, list):
                for line in value:
                    res[i] = line
                    i += 1
            elif isinstance(value, str):
                res[i] = value
                i += 1

        new_content_map = ContentMap()
        new_content_map.update(res)

        return new_content_map

    def as_content(self, apply=False, numbered=False, padded=False):
        map = self
        if apply:
            map = self.do_apply()

        lines = []

        if numbered:
            lines = [map.as_numbered_line(line, i) for i, line in map.items()]
        elif padded:
            lines = [map.as_padded_line(line) for line in map.values()]
        else:
            lines = [line for line in map.values()]

        return "".join(lines)

    def __getitem__(self, key):
        try:
            self._map[key]
        except:
            printw(key)
            for line_num, line_content in self._map.items():
                printw(f"{line_num}{line_separator}{line_content}")

        return self._map[key]

    def __setitem__(self, key, value):
        self._map[key] = value

    def __contains__(self, key):
        return key in self._map

    def __len__(self):
        return len(self._map)

    def items(self):
        return self._map.items()

    def keys(self):
        return self._map.keys()

    def values(self):
        return self._map.values()

    def get(self, key, default=None):
        return self._map.get(key, default)

    def update(self, other):
        if isinstance(other, ContentMap):
            self._applied_edits = other._applied_edits
            self._map.update(other._map)
            self._len = len(self._map)
            self._digits = math.ceil(math.log10(self._len + 1))
        else:
            self._map.update(other)
            self._len = len(self._map)
            self._digits = math.ceil(math.log10(self._len + 1))

line_separator = "│"

def parse_line(line):
    # If no separator in line, return none with whole line
    if line_separator not in line:
        return None, line

    # Split on first separator only
    parts = line.split(line_separator, 1)
    if len(parts) != 2:
        return None, line

    prefix, content = parts

    # Check if prefix is just whitespace and numbers
    cleaned = prefix.strip()
    if not cleaned or not cleaned.isdigit():
        return None, content

    try:
        return int(cleaned), content
    except ValueError:
        return None, content

def prep(content):
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines

def numbered_replace(whole_map, editblock):
    whole_map_copy = ContentMap()
    whole_map_copy.update(whole_map)

    remove_map = editblock.remove_map
    insert_map = editblock.insert_map

    remove_len = len(remove_map)
    content_len = len(whole_map_copy)

    if remove_len == 0 or content_len == 0:
        # printg("appending to the end of the file")
        whole_map_copy.apply(editblock)
        return whole_map_copy

    offsets = [0,-1,1]

    min_line = min(remove_map.keys())
    if min_line not in whole_map_copy.keys():
        if not remove_map[min_line].strip():
            # append to the end of content
            editblock_copy = EditBlock(whole_map_copy, ContentMap(), insert_map)
            whole_map_copy.apply(editblock)
            return whole_map_copy

    # Adding line number clamping to ensure we stay within valid line range
    min_line = min(whole_map_copy.keys())
    max_line = max(whole_map_copy.keys())

    for offset in offsets:
        # print(f"    (attempting offset {offset})")

        mismatch = None
        for num, line in remove_map.items():
            num_o = num + offset
            if num_o > max_line:
                # printr(f"line number ({num_o}) outside original_content range:")
                mismatch = num
                break
            if num_o < min_line:
                # printr(f"line number ({num_o}) outside original_content range:")
                mismatch = num
                break
            if num_o in whole_map_copy:
                original_line = whole_map_copy[num_o]
                similarity = SequenceMatcher(None, original_line, line).ratio()
                if original_line == line:
                    # if offset != 0:
                        # printg(f"MATCH")
                        # printg(str(num_o)+line_separator+str(line))
                    continue
                elif similarity > 0.95:
                    # if offset != 0:
                        # printg(f"MATCH (similarity: {similarity})")
                        # printg(str(num_o)+line_separator+str(line))
                    continue
                else:
                    # printr(f"NO MATCH (similarity: {similarity})")
                    # printr("<<<<<<< REMOVE")
                    # printr(str(num_o)+line_separator+str(line)+"=======")
                    # printr(str(num_o)+line_separator+str(original_line)+">>>>>>> INSERT")
                    mismatch = num
                    break
            else:
                # printr(f"line:")
                # printr(str(num_o)+line_separator+str(line))
                # printr(f"not found in original content:")
                # printr(whole_map_copy.as_content(apply=False, numbered=True))
                mismatch = num
                break

        if mismatch is None:
            offset_remove_map = ContentMap()
            for num, line in editblock.remove_map.items():
                offset_remove_map[num + offset] = line

            offset_editblock = EditBlock(whole_map_copy, offset_remove_map, insert_map)
            offset_editblock.mismatch = editblock.mismatch
            whole_map_copy.apply(offset_editblock)

            # print("Applied editblock:")
            # if offset != 0:
                # print(f"    (offset by {offset} lines)")
            # printg(editblock.as_content(numbered=True))
            return True, whole_map_copy, offset_editblock
        else:
            if offset == 0:
                editblock.mismatch = mismatch

    # print("Skipped editblock:")
    # printr(editblock.as_content(numbered=True))
    return False, whole_map_copy, editblock

def strip_quoted_wrapping(res, fname=None, fence=DEFAULT_FENCE):
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

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res

def do_replace(fname, content_map, editblock):
    fname = Path(fname)

    if not fname.exists():
        fname.touch()

    # print(f"Trying to remove {len(editblock)} lines from: {fname}")
    return numbered_replace(content_map, editblock)

def strip_filename(filename, fence):
    filename = filename.strip()

    if filename == "...":
        return

    start_fence = fence[0]
    if filename.startswith(start_fence):
        return

    filename = filename.rstrip(":")
    filename = filename.lstrip("#")
    filename = filename.strip()
    filename = filename.strip("`")
    filename = filename.strip("*")

    # https://github.com/Aider-AI/aider/issues/1158
    # filename = filename.replace("\\_", "_")

    return filename

def find_filename(lines, fence, valid_fnames):
    """
    Deepseek Coder v2 has been doing this:


     ```python
    word_count.py
    ```
    ```python
    <<<<<<< REMOVE
    ...

    This is a more flexible search back for filenames.
    """

    if valid_fnames is None:
        valid_fnames = []

    # Go back through the 3 preceding lines
    lines.reverse()
    lines = lines[:3]

    filenames = []
    for line in lines:
        # If we find a filename, done
        filename = strip_filename(line, fence)
        if filename:
            filenames.append(filename)

        # Only continue as long as we keep seeing fences
        if not line.startswith(fence[0]):
            break

    if not filenames:
        return

    # pick the *best* filename found

    # Check for exact match first
    for fname in filenames:
        if fname in valid_fnames:
            return fname

    # Check for partial match (basename match)
    for fname in filenames:
        for vfn in valid_fnames:
            if fname == Path(vfn).name:
                return vfn

    # Perform fuzzy matching with valid_fnames
    for fname in filenames:
        close_matches = difflib.get_close_matches(fname, valid_fnames, n=1, cutoff=0.8)
        if len(close_matches) == 1:
            return close_matches[0]

    # If no fuzzy match, look for a file w/extension
    for fname in filenames:
        if "." in fname:
            return fname

    if filenames:
        return filenames[0]
