#!/usr/bin/env python3

import difflib
import io
import re
import sys
import unittest

from aider.coders.base_coder import all_fences
from aider.coders.editblock_coder import find_original_update_blocks
from aider.dump import dump  # noqa: F401


def process_markdown(filename, fh):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"@@@ File '{filename}' not found.", "@" * 20, file=fh, flush=True)
        return
    except UnicodeDecodeError:
        print(
            f"@@@ File '{filename}' has an encoding issue. Make sure it's UTF-8 encoded.",
            "@" * 20,
            file=fh,
            flush=True,
        )
        return

    # Split the content into sections based on '####' headers
    sections = re.split(r"(?=####\s)", content)

    for section in sections:
        if "editblock_coder.py" in section or "test_editblock.py" in section:
            continue

        if not section.strip():  # Ignore empty sections
            continue
        # Extract the header (if present)
        header = section.split("\n")[0].strip()
        # Get the content (everything after the header)
        content = "".join(section.splitlines(keepends=True)[1:])

        for fence in all_fences[1:] + all_fences[:1]:
            if "\n" + fence[0] in content:
                break

        # Process the content with find_original_update_blocks
        try:
            blocks = list(find_original_update_blocks(content, fence))
        except ValueError as e:
            print("\n\n@@@", header, "@" * 20, file=fh, flush=True)
            print(str(e), file=fh, flush=True)
            continue

        if blocks:
            print("\n\n@@@", header, "@" * 20, file=fh, flush=True)

        for block in blocks:
            if block[0] is None:  # This is a shell command block
                print("@@@ SHELL", "@" * 20, file=fh, flush=True)
                print(block[1], end="", file=fh, flush=True)
                print("@@@ ENDSHELL", "@" * 20, file=fh, flush=True)

            else:  # This is a SEARCH/REPLACE block
                print("@@@ SEARCH:", block[0], "@" * 20, file=fh, flush=True)
                print(block[1], end="", file=fh, flush=True)
                print("@" * 20, file=fh, flush=True)
                print(block[2], end="", file=fh, flush=True)
                print("@@@ REPLACE", "@" * 20, file=fh, flush=True)


class TestFindOrBlocks(unittest.TestCase):
    def test_process_markdown(self):
        # Path to the input markdown file
        input_file = "tests/fixtures/chat-history.md"

        # Path to the expected output file
        expected_output_file = "tests/fixtures/chat-history-search-replace-gold.txt"

        # Create a StringIO object to capture the output
        output = io.StringIO()

        # Run process_markdown
        process_markdown(input_file, output)

        # Get the actual output
        actual_output = output.getvalue()

        # Read the expected output
        with open(expected_output_file, "r", encoding="utf-8") as f:
            expected_output = f.read()

        # Compare the actual and expected outputs
        if actual_output != expected_output:
            # If they're different, create a diff
            diff = difflib.unified_diff(
                expected_output.splitlines(keepends=True),
                actual_output.splitlines(keepends=True),
                fromfile=expected_output_file,
                tofile="actual output",
            )

            # Join the diff lines into a string
            diff_text = "".join(diff)

            # Fail the test and show the diff
            self.fail(f"Output doesn't match expected output. Diff:\n{diff_text}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        process_markdown(sys.argv[1], sys.stdout)
    else:
        unittest.main()
