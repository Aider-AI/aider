#!/usr/bin/env python3

import re
import sys

from aider.coders.base_coder import all_fences
from aider.coders.editblock_coder import find_original_update_blocks


def process_markdown(filename, fh):
    try:
        with open(filename, "r") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"@@@ File '{filename}' not found.", "@" * 20, file=fh, flush=True)
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python testsr.py <markdown_filename>")
    else:
        process_markdown(sys.argv[1], sys.stdout)
