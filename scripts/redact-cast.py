#!/usr/bin/env python3
import json
import os
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

        # Initialize terminal emulator
        screen = pyte.Screen(width, height)
        stream = pyte.Stream(screen)

        # Process events line by line
        for line in tqdm(fin, desc="Processing events", total=total_lines - 1):
            if not line.strip():
                continue

            event = json.loads(line)

            # Only run terminal emulation for output events
            if len(event) >= 3 and event[1] == "o":
                stream.feed(event[2])

                # Check if "Atuin" is visible on screen - exit early if found
                atuin_visible = False
                for display_line in screen.display:
                    if "Atuin" in display_line:
                        atuin_visible = True
                        break

                if atuin_visible:
                    continue  # Skip this event

            # Write event to output file
            fout.write(json.dumps(event) + "\n")


if __name__ == "__main__":
    main()
