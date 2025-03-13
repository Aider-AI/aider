#!/usr/bin/env python3
import json
import os
import re
import sys

import pyte
from tqdm import tqdm


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input_cast_file output_cast_file")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Count total lines for progress bar
    total_lines = sum(1 for _ in open(input_file, "r"))

    with open(input_file, "r") as fin, open(output_file, "w") as fout:
        # Process header
        header = fin.readline().strip()
        fout.write(header + "\n")

        # Parse header for terminal dimensions
        header_data = json.loads(header)
        width = header_data.get("width", 80)
        height = header_data.get("height", 24)
        print(f"Terminal dimensions: {width}x{height}")

        # Initialize terminal emulator but don't use it unless necessary
        screen = pyte.Screen(width, height)
        stream = pyte.Stream(screen)

        # Track if we need to check the terminal (if "Atuin" might be on screen)
        check_terminal = False
        atuin_pattern = re.compile(r"A.*t.*u.*i.*n")

        # Process events line by line
        for line in tqdm(fin, desc="Processing events", total=total_lines - 1):
            if not line.strip():
                continue

            # Fast initial check on raw line before JSON parsing
            raw_line_has_atuin = bool(atuin_pattern.search(line))

            if raw_line_has_atuin:
                check_terminal = True

            # Only parse JSON if we're checking terminal or need to check
            if not check_terminal:
                fout.write(line)
                continue

            event = json.loads(line)

            if not (len(event) >= 3 and event[1] == "o"):
                fout.write(line)
                continue

            output_text = event[2]

            stream.feed(output_text)

            # Check if "Atuin" is visible on screen
            atuin_visible = False
            for display_line in screen.display:
                if "Atuin" in "".join(display_line):
                    atuin_visible = True
                    break

            # Reset flag if Atuin is no longer visible
            check_terminal = atuin_visible

            if not atuin_visible:
                fout.write(line)


if __name__ == "__main__":
    main()
