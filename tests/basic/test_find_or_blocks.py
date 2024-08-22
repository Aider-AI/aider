#!/usr/bin/env python3

import json
import re
import sys

# from aider.coders.base_coder import all_fences
from aider.coders.editblock_coder import find_original_update_blocks


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


all_fences = [
    ("``" + "`", "``" + "`"),
    wrap_fence("source"),
    wrap_fence("code"),
    wrap_fence("pre"),
    wrap_fence("codeblock"),
    wrap_fence("sourcecode"),
]


def process_markdown(filename):
    try:
        with open(filename, "r") as file:
            content = file.read()
    except FileNotFoundError:
        print(f"@@@ File '{filename}' not found.", "@" * 20)
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
            print("\n\n@@@", header, "@" * 20)
            print(str(e))
            continue

        if blocks:
            print("\n\n@@@", header, "@" * 20)

        for block in blocks:
            if block[0] is None:  # This is a shell command block
                print("@@@ SHELL", "@" * 20)
                print(block[1], end="")
                print("@@@ ENDSHELL", "@" * 20)

            else:  # This is a SEARCH/REPLACE block
                print("@@@ SEARCH:", block[0], "@" * 20)
                print(block[1], end="")
                print("@" * 20)
                print(block[2], end="")
                print("@@@ REPLACE", "@" * 20)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python testsr.py <markdown_filename>"}, indent=4))
    else:
        process_markdown(sys.argv[1])
