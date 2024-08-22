#!/usr/bin/env python3

import json
import re
import sys

from aider.coders.editblock_coder import (
    DEFAULT_FENCE,
    find_original_update_blocks,
)
from aider.coders.base_coder import all_fences


def process_markdown(filename):
    try:
        with open(filename, "r") as file:
            content = file.read()
    except FileNotFoundError:
        print(json.dumps({"error": f"File '{filename}' not found."}, indent=4))
        return

    # Split the content into sections based on '####' headers
    sections = re.split(r"(?=####\s)", content)

    results = []
    for section in sections:
            if not section.strip():  # Ignore empty sections
                continue
            # Extract the header (if present)
            header = section.split("\n")[0].strip()
            # Get the content (everything after the header)
            content = "\n".join(section.split("\n")[1:]).strip()

            for fence in all_fences:
                if '\n' + fence[0] in content:
                    break

            # Process the content with find_original_update_blocks
            try:
                blocks = list(find_original_update_blocks(content, fence))
            except ValueError as e:
                # If an error occurs, add it to the results for this section
                results.append({"header": header, "error": str(e)})
                continue

            # Create a dictionary for this section
            section_result = {"header": header, "blocks": []}

            for block in blocks:
                if block[0] is None:  # This is a shell command block
                    section_result["blocks"].append({"type": "shell", "content": block[1]})
                else:  # This is a SEARCH/REPLACE block
                    section_result["blocks"].append(
                        {
                            "type": "search_replace",
                            "filename": block[0],
                            "original": block[1],
                            "updated": block[2],
                        }
                    )

            results.append(section_result)

        # Output the results as JSON
        print(json.dumps(results, indent=4))

    except FileNotFoundError:
        print(json.dumps({"error": f"File '{filename}' not found."}, indent=4))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python testsr.py <markdown_filename>"}, indent=4))
    else:
        process_markdown(sys.argv[1])
