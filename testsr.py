import json
import re
import sys

from aider.coders.editblock_coder import DEFAULT_FENCE, find_original_update_blocks


def process_markdown(filename):
    try:
        with open(filename, "r") as file:
            content = file.read()

        # Split the content into sections based on '####' headers
        sections = re.split(r"(?=####\s)", content)

        results = []
        for section in sections:
            if section.strip():  # Ignore empty sections
                # Extract the header (if present)
                header = section.split("\n")[0].strip()
                # Get the content (everything after the header)
                content = "\n".join(section.split("\n")[1:]).strip()

                # Process the content with find_original_update_blocks
                blocks = list(find_original_update_blocks(content, DEFAULT_FENCE))

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
        print(json.dumps(results, indent=2))

    except FileNotFoundError:
        print(json.dumps({"error": f"File '{filename}' not found."}))
    except Exception as e:
        print(json.dumps({"error": f"An error occurred: {str(e)}"}))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python testsr.py <markdown_filename>"}))
    else:
        process_markdown(sys.argv[1])
