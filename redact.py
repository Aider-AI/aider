#!/usr/bin/env python3
import re
import sys
import os

def process_file(input_path, output_path):
    """
    Process a text file to filter out certain sections based on ANSI cursor commands.

    If a line contains "\u001b[ROW;COL]H" followed by "Atuin", skip it and all subsequent
    lines until finding a line with "\u001b[ROW;(COL-1)H".
    """
    skip_mode = False
    target_pattern = None
    ansi_pattern = re.compile(r'\\u001b\[(\d+);(\d+)H')

    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            # If we're not in skip mode, check if we need to enter it
            if not skip_mode:
                if '\\u001b[' in line and 'Atuin' in line:
                    match = ansi_pattern.search(line)
                    if match:
                        row = match.group(1)
                        col = int(match.group(2))
                        # Create pattern for the line that will end the skip section
                        target_pattern = f'\\u001b[{row};{col-1}H'
                        skip_mode = True
                        continue  # Skip this line
                # If we're not skipping, write the line
                outfile.write(line)
            # If we're in skip mode, check if we should exit it
            else:
                if target_pattern in line:
                    skip_mode = False
                    outfile.write(line)  # Include the matching line

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {os.path.basename(sys.argv[0])} input_file output_file")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        sys.exit(1)

    process_file(input_file, output_file)
    print(f"Processed {input_file} -> {output_file}")
