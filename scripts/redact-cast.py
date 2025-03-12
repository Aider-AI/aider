#!/usr/bin/env python3
import json
import os
import re
import sys

# Speed up factor for the recording
SPEEDUP = 1.25

# Regular expression to match ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\([0-9A-Z=])")


def strip_ansi(text):
    """Remove ANSI escape sequences from text"""
    return ANSI_ESCAPE_PATTERN.sub("", text)


def process_file(input_path, output_path):
    """
    Process an asciinema cast v2 file to filter out certain sections based on ANSI cursor commands.

    Format: First line is a JSON header. Subsequent lines are JSON arrays: [timestamp, "o", "text"]

    If a text field contains "\u001b[ROW;COL]H" followed by "Atuin", skip it and all subsequent
    records until finding a text with "\u001b[ROW;(COL-1)H".

    Maintains consistent timestamps by:
    1. Not advancing time during skip sections
    2. Compressing any long gaps to 0.5 seconds maximum
    """
    skip_mode = False
    target_pattern = None
    ansi_pattern = re.compile(r"\u001b\[(\d+);(\d+)H")
    is_first_line = True
    last_timestamp = 0.0
    time_offset = 0.0  # Accumulator for time to subtract
    max_gap = 0.5  # Maximum allowed time gap between events

    with (
        open(input_path, "r", encoding="utf-8") as infile,
        open(output_path, "w", encoding="utf-8") as outfile,
    ):
        for line in infile:
            # Process the header (first line)
            if is_first_line:
                try:
                    header = json.loads(line)
                    if "env" in header:
                        del header["env"]
                    outfile.write(json.dumps(header) + "\n")
                except json.JSONDecodeError:
                    # If we can't parse the header, keep it as is
                    outfile.write(line)
                is_first_line = False
                continue

            # Parse the JSON record
            try:
                record = json.loads(line)
                if not isinstance(record, list) or len(record) != 3 or record[1] != "o":
                    # If not a valid record, just write it out
                    outfile.write(line)
                    continue

                current_timestamp = float(record[0])
                text = record[2]  # The text content

                # If we're not in skip mode, check if we need to enter it
                if not skip_mode:
                    # First check for cursor positioning command
                    if "\u001b[" in text:
                        match = ansi_pattern.search(text)
                        if match and "Atuin" in strip_ansi(text):
                            row = match.group(1)
                            col = int(match.group(2))
                            # Create pattern for the ending sequence
                            target_pattern = f"\u001b[{row};{col - 1}H"
                            skip_mode = True
                            # Start tracking time to subtract
                            skip_start_time = current_timestamp
                            continue  # Skip this record

                    # If we're not skipping, write the record with adjusted timestamp
                    # First, adjust for skipped sections
                    adjusted_timestamp = current_timestamp - time_offset

                    # Then, check if there's a long gap to compress
                    if last_timestamp > 0:
                        time_gap = adjusted_timestamp - last_timestamp
                        if time_gap > max_gap:
                            # Compress the gap and add the excess to time_offset
                            excess_time = time_gap - max_gap
                            time_offset += excess_time
                            adjusted_timestamp -= excess_time

                    # Ensure timestamps never go backward
                    adjusted_timestamp = max(adjusted_timestamp, last_timestamp)
                    last_timestamp = adjusted_timestamp
                    # Apply speedup factor to the timestamp
                    record[0] = adjusted_timestamp / SPEEDUP
                    outfile.write(json.dumps(record) + "\n")

                # If we're in skip mode, check if we should exit it
                else:
                    if target_pattern in text:
                        skip_mode = False
                        # Calculate how much time to subtract from future timestamps
                        time_offset += current_timestamp - skip_start_time

                        # Add a 0.5 second pause after each skip section
                        last_timestamp += 0.5

                        # Write this record with adjusted timestamp
                        adjusted_timestamp = current_timestamp - time_offset

                        # Check if there's a long gap to compress
                        if last_timestamp > 0:
                            time_gap = adjusted_timestamp - last_timestamp
                            if time_gap > max_gap:
                                # Compress the gap and add the excess to time_offset
                                excess_time = time_gap - max_gap
                                time_offset += excess_time
                                adjusted_timestamp -= excess_time

                        # Ensure timestamps never go backward
                        adjusted_timestamp = max(adjusted_timestamp, last_timestamp)
                        last_timestamp = adjusted_timestamp
                        # Apply speedup factor to the timestamp
                        record[0] = adjusted_timestamp / SPEEDUP
                        outfile.write(json.dumps(record) + "\n")
                    # Otherwise we're still in skip mode, don't write anything

            except json.JSONDecodeError:
                # If we can't parse the line as JSON, include it anyway
                outfile.write(line)


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
