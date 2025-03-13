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

    # Read and parse the cast file
    with open(input_file, "r") as f:
        # First line is header
        header = f.readline().strip()

        # Parse header to extract terminal dimensions
        header_data = json.loads(header)
        width = header_data.get("width", 80)
        height = header_data.get("height", 24)
        
        print(f"Terminal dimensions: {width}x{height}")

        # Initialize pyte screen and stream with dimensions from header
        screen = pyte.Screen(width, height)
        stream = pyte.Stream(screen)

        # Read the events
        events = [json.loads(line) for line in f if line.strip()]

    # Write the header to the output file
    with open(output_file, "w") as f:
        f.write(header + "\n")

        # Process each event through the terminal emulator and stream to file
        for event in tqdm(events, desc="Processing events"):
            # Process the event in the terminal
            if len(event) >= 3 and event[1] == "o":  # Output event
                stream.feed(event[2])

                # Check if "Atuin" is visible on screen
                display_content = "\n".join("".join(line) for line in screen.display)
                if "Atuin" in display_content:
                    continue  # Skip this event

            # Write this event directly to the output file
            f.write(json.dumps(event) + "\n")


if __name__ == "__main__":
    main()
