import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
import re
import difflib

import oslex

from aider.dump import dump  # noqa: F401
from aider.waiting import Spinner

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".pdf"}

# From aider/coders/editblock_coder.py
# Constants for edit block parsing
DEFAULT_FENCE = ("```", "```")
triple_backticks = "`" * 3
QUAD_BACKTICKS = "`" * 4

# Original edit block format markers
# HEAD = r"^<{5,9} SEARCH\s*$"
# DIVIDER = r"^={5,9}\s*$"
# UPDATED = r"^>{5,9} REPLACE\s*$"

# HEAD_ERR = "<<<<<<< SEARCH"
# DIVIDER_ERR = "======="
# UPDATED_ERR = ">>>>>>> REPLACE"

# New, more flexible edit block format markers (allow variations)
HEAD = r"^<{5,9}\s*SEARCH\s*(.*)$\n|```diff\n--- a/(.*?)\n\+\+\+ b/\1\n"
DIVIDER = r"^[-=~\*]{5,}$\n"
UPDATED = r"^>{5,9}\s*REPLACE\s*$\n"

HEAD_FMT = "<<<<<<< SEARCH{}"
DIVIDER_FMT = "======="
UPDATED_FMT = ">>>>>>> REPLACE"

HEAD_ERR = HEAD_FMT.format("")
DIVIDER_ERR = DIVIDER_FMT
UPDATED_ERR = UPDATED_FMT


missing_filename_err = '''\
The edit block is missing a filename.
To specify the filename, use a line like this before the `{fence[0]}` line:

{fence[0]}python
example.py
{fence[1]}
'''

# end From aider/coders/editblock_coder.py


class IgnorantTemporaryDirectory:
    def __init__(self):
        if sys.version_info >= (3, 10):
            self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        else:
            self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.temp_dir.cleanup()
        except (OSError, PermissionError, RecursionError):
            pass  # Ignore errors (Windows and potential recursion)

    def __getattr__(self, item):
        return getattr(self.temp_dir, item)


class ChdirTemporaryDirectory(IgnorantTemporaryDirectory):
    def __init__(self):
        try:
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.cwd = None

        super().__init__()

    def __enter__(self):
        res = super().__enter__()
        os.chdir(Path(self.temp_dir.name).resolve())
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cwd:
            try:
                os.chdir(self.cwd)
            except FileNotFoundError:
                pass
        super().__exit__(exc_type, exc_val, exc_tb)


class GitTemporaryDirectory(ChdirTemporaryDirectory):
    def __enter__(self):
        dname = super().__enter__()
        self.repo = make_repo(dname)
        return dname

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.repo
        super().__exit__(exc_type, exc_val, exc_tb)


def make_repo(path=None):
    import git

    if not path:
        path = "."
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "testuser@example.com").release()

    return repo


def is_image_file(file_name):
    """
    Check if the given file name has an image file extension.

    :param file_name: The name of the file to check.
    :return: True if the file is an image, False otherwise.
    """
    file_name = str(file_name)  # Convert file_name to string
    return any(file_name.endswith(ext) for ext in IMAGE_EXTENSIONS)


def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)


def format_content(role, content):
    formatted_lines = []
    for line in content.splitlines():
        formatted_lines.append(f"{role} {line}")
    return "\n".join(formatted_lines)


def format_messages(messages, title=None):
    output = []
    if title:
        output.append(f"{title.upper()} {'*' * 50}")

    for msg in messages:
        output.append("-------")
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, dict) and "url" in value:
                            output.append(f"{role} {key.capitalize()} URL: {value['url']}")
                        else:
                            output.append(f"{role} {key}: {value}")
                else:
                    output.append(f"{role} {item}")
        elif isinstance(content, str):  # Handle string content
            output.append(format_content(role, content))
        function_call = msg.get("function_call")
        if function_call:
            output.append(f"{role} Function Call: {function_call}")

    return "\n".join(output)


def show_messages(messages, title=None, functions=None):
    formatted_output = format_messages(messages, title)
    print(formatted_output)

    if functions:
        dump(functions)


def split_chat_history_markdown(text, include_tool=False):
    messages = []
    user = []
    assistant = []
    tool = []
    lines = text.splitlines(keepends=True)

    def append_msg(role, lines):
        lines = "".join(lines)
        if lines.strip():
            messages.append(dict(role=role, content=lines))

    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("> "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("user", user)
            user = []
            tool.append(line[2:])
            continue
        # if line.startswith("#### /"):
        #    continue

        if line.startswith("#### "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("tool", tool)
            tool = []

            content = line[5:]
            user.append(content)
            continue

        append_msg("user", user)
        user = []
        append_msg("tool", tool)
        tool = []

        assistant.append(line)

    append_msg("assistant", assistant)
    append_msg("user", user)

    if not include_tool:
        messages = [m for m in messages if m["role"] != "tool"]

    return messages


def get_pip_install(args):
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--upgrade-strategy",
        "only-if-needed",
    ]
    cmd += args
    return cmd


def run_install(cmd):
    print()
    print("Installing:", printable_shell_command(cmd))

    try:
        output = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding=sys.stdout.encoding,
            errors="replace",
        )
        spinner = Spinner("Installing...")

        while True:
            char = process.stdout.read(1)
            if not char:
                break

            output.append(char)
            spinner.step()

        spinner.end()
        return_code = process.wait()
        output = "".join(output)

        if return_code == 0:
            print("Installation complete.")
            print()
            return True, output

    except subprocess.CalledProcessError as e:
        print(f"\nError running pip install: {e}")

    print("\nInstallation failed.\n")

    return False, output


def find_common_root(abs_fnames):
    try:
        if len(abs_fnames) == 1:
            return safe_abs_path(os.path.dirname(list(abs_fnames)[0]))
        elif abs_fnames:
            return safe_abs_path(os.path.commonpath(list(abs_fnames)))
    except OSError:
        pass

    try:
        return safe_abs_path(os.getcwd())
    except FileNotFoundError:
        # Fallback if cwd is deleted
        return "."


def format_tokens(count):
    if count < 1000:
        return f"{count}"
    elif count < 10000:
        return f"{count / 1000:.1f}k"
    else:
        return f"{round(count / 1000)}k"


def touch_file(fname):
    fname = Path(fname)
    try:
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.touch()
        return True
    except OSError:
        return False


def check_pip_install_extra(io, module, prompt, pip_install_cmd, self_update=False):
    if module:
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError, RuntimeError):
            pass

    cmd = get_pip_install(pip_install_cmd)

    if prompt:
        io.tool_warning(prompt)

    if self_update and platform.system() == "Windows":
        io.tool_output("Run this command to update:")
        print()
        print(printable_shell_command(cmd))  # plain print so it doesn't line-wrap
        return

    if not io.confirm_ask("Run pip install?", default="y", subject=printable_shell_command(cmd)):
        return

    success, output = run_install(cmd)
    if success:
        if not module:
            return True
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError, RuntimeError) as err:
            io.tool_error(str(err))
            pass

    io.tool_error(output)

    print()
    print("Install failed, try running this command manually:")
    print(printable_shell_command(cmd))


def printable_shell_command(cmd_list):
    """
    Convert a list of command arguments to a properly shell-escaped string.

    Args:
        cmd_list (list): List of command arguments.

    Returns:
        str: Shell-escaped command string.
    """
    return " ".join(oslex.quote(s) for s in cmd_list)


# From aider/coders/editblock_coder.py
def find_original_update_blocks(content, fence=DEFAULT_FENCE, valid_fnames=None):
    lines = content.splitlines(keepends=True)
    i = 0
    current_filename = None

    head_pattern = re.compile(HEAD)
    divider_pattern = re.compile(DIVIDER)
    updated_pattern = re.compile(UPDATED)

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

        # Check if the next line or the one after that is an editblock
        next_is_editblock = (
            i + 1 < len(lines)
            and head_pattern.match(lines[i + 1].strip())
            or i + 2 < len(lines)
            and head_pattern.match(lines[i + 2].strip())
        )

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

        # Check for SEARCH/REPLACE blocks
        if head_pattern.match(line.strip()):
            try:
                # if next line after HEAD exists and is DIVIDER, it\'s a new file
                if i + 1 < len(lines) and divider_pattern.match(lines[i + 1].strip()):
                    filename = find_filename(lines[max(0, i - 3) : i], fence, None)
                else:
                    filename = find_filename(lines[max(0, i - 3) : i], fence, valid_fnames)

                if not filename:
                    if current_filename:
                        filename = current_filename
                    else:
                        raise ValueError(missing_filename_err.format(fence=fence))

                current_filename = filename

                original_text = []
                i += 1
                while i < len(lines) and not divider_pattern.match(lines[i].strip()):
                    original_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not divider_pattern.match(lines[i].strip()):
                    raise ValueError(f"Expected `{DIVIDER_ERR}`")

                updated_text = []
                i += 1
                while i < len(lines) and not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    updated_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    raise ValueError(f"Expected `{UPDATED_ERR}` or `{DIVIDER_ERR}`")

                yield filename, "".join(original_text), "".join(updated_text)

            except ValueError as e:
                processed = "".join(lines[: i + 1])
                err = e.args[0]
                raise ValueError(f"{processed}\\n^^^ {err}")

        i += 1


def find_filename(lines, fence, valid_fnames):
    """
    Deepseek Coder v2 has been doing this:


     ```python
    word_count.py
    ```
    ```python
    <<<<<<< SEARCH
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
        if not line.startswith(fence[0]) and not line.startswith(triple_backticks):
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

def strip_filename(filename, fence):
    """
    Extracts the filename from a line that might be part of a fenced code block
    or a simple filename.
    Handles cases like:
    ```python
    example.py
    ```
    example.py
    """
    filename = filename.strip()

    # If it\'s wrapped in a fence, extract it
    if filename.startswith(fence[0]) and filename.endswith(fence[1]):
        # This regex tries to capture the content between the opening fence (possibly with a language specifier)
        # and the closing fence.
        # It handles:
        # ```python\npath/to/file.py\n```
        # ```\npath/to/file.py\n```
        match = re.match(rf"^{re.escape(fence[0])}[a-zA-Z0-9_]*\s*(.*?)\s*{re.escape(fence[1])}$", filename, re.DOTALL)
        if match:
            filename = match.group(1).strip()
        else: # Fallback for simple fence without language
            if filename.startswith(fence[0]):
                filename = filename[len(fence[0]):]
            if filename.endswith(fence[1]):
                filename = filename[:-len(fence[1])]
            filename = filename.strip()


    # It might also be a path that the LLM just prints
    # Remove backticks if they are not part of a proper fence
    if filename.startswith("`") and filename.endswith("`") and not (filename.startswith(triple_backticks) or filename.startswith(QUAD_BACKTICKS)):
        filename = filename[1:-1]

    # Reject if it looks like a diff/patch header
    if filename.startswith("--- a/") or filename.startswith("+++ b/"):
        return None
    if filename.startswith("diff --git"):
        return None

    # If it contains newlines, it's probably not just a filename
    if "\\n" in filename or "\\r" in filename:
        return None
        
    # Check if it's a valid-looking filename (very basic check)
    # Avoids matching random ```python or other non-filename lines
    if not re.match(r"^[a-zA-Z0-9_./\\-][a-zA-Z0-9_.\s/\\-]*$", filename):
        return None
        
    # Reject if it is just a language name
    common_languages = ['python', 'javascript', 'java', 'csharp', 'cpp', 'ruby', 'go', 'php', 'swift', 'kotlin', 'rust', 'typescript', 'html', 'css', 'sql', 'bash', 'shell']
    if filename.lower() in common_languages:
        return None

    return filename if filename else None

# Need to import re and difflib for the above functions
import re
import difflib

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
        raise ValueError("Unpaired ... in SEARCH/REPLACE block")

    if len(part_pieces) == 1:
        # no dots in this edit block, just return None
        return

    # Compare odd strings in part_pieces and replace_pieces
    all_dots_match = all(part_pieces[i] == replace_pieces[i] for i in range(1, len(part_pieces), 2))

    if not all_dots_match:
        raise ValueError("Unmatched ... in SEARCH/REPLACE block")

    part_pieces = [part_pieces[i] for i in range(0, len(part_pieces), 2)]
    replace_pieces = [replace_pieces[i] for i in range(0, len(replace_pieces), 2)]

    pairs = zip(part_pieces, replace_pieces)
    for part_piece, replace_piece in pairs: # renamed loop vars to avoid conflict
        if not part_piece and not replace_piece:
            continue

        if not part_piece and replace_piece:
            if not whole.endswith("\n"):
                whole += "\n"
            whole += replace_piece
            continue

        if whole.count(part_piece) == 0:
            raise ValueError("A piece of the SEARCH block (delimited by '...') was not found in the original content.")
        if whole.count(part_piece) > 1:
            raise ValueError("A piece of the SEARCH block (delimited by '...') was found multiple times in the original content. This is ambiguous.")

        whole = whole.replace(part_piece, replace_piece, 1)

    return whole

# end From aider/coders/editblock_coder.py


# From aider/coders/editblock_coder.py (edit application helpers)
def prep(content):
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines

def perfect_or_whitespace(whole_lines, part_lines, replace_lines):
    # Try for a perfect match
    res = perfect_replace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    # Try being flexible about leading whitespace
    res = replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res

def perfect_replace(whole_lines, part_lines, replace_lines):
    part_tup = tuple(part_lines)
    part_len = len(part_lines)

    for i in range(len(whole_lines) - part_len + 1):
        whole_tup = tuple(whole_lines[i : i + part_len])
        if part_tup == whole_tup:
            res = whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
            return "".join(res)

def replace_most_similar_chunk(whole, part, replace):
    """Best efforts to find the `part` lines in `whole` and replace them with `replace`"""

    whole, whole_lines = prep(whole)
    part, part_lines = prep(part)
    replace, replace_lines = prep(replace)

    res = perfect_or_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res

    # drop leading empty line, GPT sometimes adds them spuriously (issue #25)
    if len(part_lines) > 2 and not part_lines[0].strip():
        skip_blank_line_part_lines = part_lines[1:]
        res = perfect_or_whitespace(whole_lines, skip_blank_line_part_lines, replace_lines)
        if res:
            return res

    # Try to handle when it elides code with ...
    try:
        res = try_dotdotdots(whole, part, replace)
        if res:
            return res
    except ValueError:
        pass

    return
    # Try fuzzy matching
    # This was commented out in the original, keeping it commented.
    # res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)
    # if res:
    #     return res

def replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines):
    # GPT often messes up leading whitespace.
    # It usually does it uniformly across the ORIG and UPD blocks.
    # Either omitting all leading whitespace, or including only some of it.

    # Outdent everything in part_lines and replace_lines by the max fixed amount possible
    leading = [len(p) - len(p.lstrip()) for p in part_lines if p.strip()] + \
              [len(p) - len(p.lstrip()) for p in replace_lines if p.strip()]

    if leading and min(leading):
        num_leading = min(leading)
        part_lines = [p[num_leading:] if p.strip() else p for p in part_lines]
        replace_lines = [p[num_leading:] if p.strip() else p for p in replace_lines]

    # can we find an exact match not including the leading whitespace
    num_part_lines = len(part_lines)

    for i in range(len(whole_lines) - num_part_lines + 1):
        add_leading = match_but_for_leading_whitespace(
            whole_lines[i : i + num_part_lines], part_lines
        )

        if add_leading is None:
            continue

        replace_lines = [add_leading + rline if rline.strip() else rline for rline in replace_lines]
        whole_lines = whole_lines[:i] + replace_lines + whole_lines[i + num_part_lines :]
        return "".join(whole_lines)

    return None

def match_but_for_leading_whitespace(whole_lines, part_lines):
    num = len(whole_lines)

    # does the non-whitespace all agree?
    if not all(whole_lines[i].lstrip() == part_lines[i].lstrip() for i in range(num)):
        return

    # are they all offset the same?
    add = set(
        whole_lines[i][: len(whole_lines[i]) - len(part_lines[i])] # Corrected slice
        for i in range(num)
        if whole_lines[i].strip()
    )

    if len(add) != 1:
        return

    return add.pop()

# replace_closest_edit_distance was not moved as it was commented out in the original.

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

    if fname and res and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res and res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and not res.endswith("\n"):
        res += "\n"

    return res

def do_replace(fname, content, before_text, after_text, fence=None):
    if fence is None: # Added default for fence if not provided from EditBlockCoder call site
        fence = DEFAULT_FENCE

    before_text = strip_quoted_wrapping(before_text, fname, fence)
    after_text = strip_quoted_wrapping(after_text, fname, fence)
    # Convert fname to Path for os-agnostic operations, and ensure it's absolute if it makes sense
    # However, fname is usually relative in this context. For now, keep as is.
    # resolved_fname = Path(fname).resolve() # Careful if fname can be abstract like "NEW_FILE.txt"
    path_obj = Path(fname) 


    # does it want to make a new file?
    # Use original fname for exists check as it might be relative from coder root
    if not Path(fname).exists() and not before_text.strip():
        # To be safe, let the caller handle file creation if path_obj needs it.
        # This function should focus on content replacement.
        # For now, if file doesn't exist and before_text is empty, assume new content is just after_text.
        # This part needs to be handled carefully by the caller (AgentCoder)
        # For now, returning after_text to indicate this is the new content for a new file.
        if not Path(fname).parent.exists():
            Path(fname).parent.mkdir(parents=True, exist_ok=True)
        Path(fname).touch()
        content = ""

    if content is None: # File existed but couldn't be read by caller
        return None

    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
    else:
        new_content = replace_most_similar_chunk(content, before_text, after_text)

    return new_content


def find_similar_lines(search_lines_str, content_str, threshold=0.6):
    search_lines = search_lines_str.splitlines()
    content_lines = content_str.splitlines()
    
    if not search_lines or not content_lines: # Handle empty inputs
        return ""

    best_ratio = 0
    best_match_chunk = None # Renamed for clarity
    best_match_start_index = -1 # Renamed for clarity

    # Iterate over all possible subsegments of content_lines that have the same length as search_lines
    for i in range(len(content_lines) - len(search_lines) + 1):
        current_chunk = content_lines[i : i + len(search_lines)]
        # Use SequenceMatcher from difflib (already imported in utils.py)
        # Ensure SequenceMatcher is imported if not already: import difflib
        ratio = difflib.SequenceMatcher(None, search_lines, current_chunk).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match_chunk = current_chunk
            best_match_start_index = i

    if best_ratio < threshold:
        return ""

    # If a good match is found, expand the context slightly for better usability
    # (similar to original logic but using renamed vars)
    if best_match_chunk and best_match_chunk[0] == search_lines[0] and best_match_chunk[-1] == search_lines[-1]:
        return "\n".join(best_match_chunk)

    # Context expansion logic
    N = 5 # Number of lines of context to add before and after
    context_start = max(0, best_match_start_index - N)
    # Ensure end_index for chunking is within bounds of content_lines
    context_end = min(len(content_lines), best_match_start_index + len(search_lines) + N) 
    
    expanded_context_chunk = content_lines[context_start:context_end]
    return "\n".join(expanded_context_chunk)

# Need to import math for replace_closest_edit_distance if it were to be used.
# import math
# Also SequenceMatcher is used by find_similar_lines, ensure difflib is imported.
