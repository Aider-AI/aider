#!/usr/bin/env python

import difflib
import json
import re
from pathlib import Path

import json5


def find_block_lines(lines, key_to_remove):
    """Finds the start and end line indices for a top-level key's block."""
    start_line_idx = -1
    # Regex to find the line starting the key definition, allowing for whitespace
    # and ensuring it's the key we want (e.g., avoid matching "key1_extra": ...)
    key_pattern = re.compile(r'^\s*"' + re.escape(key_to_remove) + r'"\s*:\s*{?')

    for i, line in enumerate(lines):
        if key_pattern.match(line.strip()):
            start_line_idx = i
            break

    if start_line_idx == -1:
        # Key might not start with '{' on the same line, check if it starts immediately after
        key_pattern_no_brace = re.compile(r'^\s*"' + re.escape(key_to_remove) + r'"\s*:\s*$')
        for i, line in enumerate(lines):
            if key_pattern_no_brace.match(line.strip()):
                # Look for the opening brace on the next non-empty/comment line
                j = i + 1
                while j < len(lines):
                    stripped_next_line = lines[j].strip()
                    if not stripped_next_line or stripped_next_line.startswith("//"):
                        j += 1
                        continue
                    if stripped_next_line.startswith("{"):
                        start_line_idx = i  # Start from the key definition line
                        break
                    else:
                        # False alarm, the line after the key wasn't '{'
                        break
                if start_line_idx != -1:
                    break

    if start_line_idx == -1:
        print(
            f"Warning: Could not reliably find start line for '{key_to_remove}'. Skipping removal."
        )
        return None, None  # Key block start not found clearly

    brace_level = 0
    in_string = False
    block_started = False
    end_line_idx = -1

    # Start brace counting from the identified start line
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        # Simple brace counting - might be fooled by braces in comments or strings
        # This is a limitation of pure text processing without full parsing
        for char_idx, char in enumerate(line):
            # Rudimentary string detection
            if char == '"':
                # Check if preceded by an odd number of backslashes (escaped quote)
                backslashes = 0
                temp_idx = char_idx - 1
                while temp_idx >= 0 and line[temp_idx] == "\\":
                    backslashes += 1
                    temp_idx -= 1
                if backslashes % 2 == 0:
                    in_string = not in_string

            if not in_string:
                if char == "{":
                    brace_level += 1
                    block_started = True  # Mark that we've entered the block
                elif char == "}":
                    brace_level -= 1

        # Check if the block ends *after* processing the entire line
        if block_started and brace_level == 0:
            end_line_idx = i
            break

    if end_line_idx == -1:
        print(
            f"Warning: Could not find end of block for '{key_to_remove}' starting at line"
            f" {start_line_idx + 1}. Skipping removal."
        )
        return None, None  # Block end not found

    return start_line_idx, end_line_idx


def remove_block_surgically(file_path, key_to_remove):
    """Reads the file, removes the block for the key, writes back."""
    try:
        # Read with universal newlines, but keep track for writing
        with open(file_path, "r") as f:
            content = f.read()
            lines = content.splitlines(keepends=True)  # Keep original line endings
    except Exception as e:
        print(f"Error reading {file_path} for removal: {e}")
        return False

    start_idx, end_idx = find_block_lines(lines, key_to_remove)

    if start_idx is None or end_idx is None:
        return False  # Error message already printed by find_block_lines

    # Prepare the lines to be written, excluding the identified block
    output_lines = lines[:start_idx] + lines[end_idx + 1 :]

    # Note: Comma handling is omitted for simplicity. User may need manual fix.

    try:
        with open(file_path, "w") as f:
            f.writelines(output_lines)
        print(f"Successfully removed '{key_to_remove}' block and updated {file_path}.")
        return True
    except Exception as e:
        print(f"Error writing updated data to {file_path} after removing {key_to_remove}: {e}")
        return False


def main():
    script_dir = Path(__file__).parent.resolve()
    # Adjust path relative to the script's location in the aider repo
    litellm_path = script_dir.parent / "../litellm/model_prices_and_context_window.json"
    aider_path = script_dir / "../aider/resources/model-metadata.json"

    if not litellm_path.exists():
        print(f"Error: LiteLLM metadata file not found at {litellm_path}")
        return

    if not aider_path.exists():
        print(f"Error: Aider metadata file not found at {aider_path}")
        return

    try:
        with open(litellm_path, "r") as f:
            litellm_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {litellm_path}: {e}")
        return
    except Exception as e:
        print(f"Error reading {litellm_path}: {e}")
        return

    try:
        # Use json5 for the aider metadata file as it might contain comments
        with open(aider_path, "r") as f:
            aider_data = json5.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {aider_path}: {e}")
        return
    except Exception as e:
        print(f"Error reading {aider_path}: {e}")
        return

    litellm_keys = set(litellm_data.keys())
    aider_keys = set(aider_data.keys())

    common_keys = sorted(list(litellm_keys.intersection(aider_keys)))
    removed_count = 0

    if common_keys:
        print("Comparing common models found in both files:\n")
        for key in common_keys:
            print(f"--- {key} (aider) ---")
            print(f"+++ {key} (litellm) +++")

            litellm_entry = litellm_data.get(key, {})
            aider_entry = aider_data.get(key, {})

            # Convert dicts to formatted JSON strings for comparison
            # First, compare the dictionaries directly for semantic equality
            if litellm_entry == aider_entry:
                print(f"'{key}': Entries are semantically identical.")
                print("\n" + "=" * 40)
                print("-" * 40 + "\n")  # Separator for the next model
                continue  # Skip diff and removal prompt for identical entries

            # Generate unified diff
            # If dictionaries differ, generate JSON strings to show the diff
            # Add a dummy key to ensure the *real* last key gets a comma
            litellm_entry_copy = litellm_entry.copy()
            aider_entry_copy = aider_entry.copy()
            dummy_key = "zzzdummykey"
            litellm_entry_copy[dummy_key] = True
            aider_entry_copy[dummy_key] = True

            litellm_json_lines = json.dumps(
                litellm_entry_copy, indent=4, sort_keys=True
            ).splitlines()
            aider_json_lines = json.dumps(aider_entry_copy, indent=4, sort_keys=True).splitlines()

            # Remove the dummy key line before diffing
            litellm_json_filtered = [line for line in litellm_json_lines if dummy_key not in line]
            aider_json_filtered = [line for line in aider_json_lines if dummy_key not in line]

            diff = difflib.unified_diff(
                aider_json_filtered,
                litellm_json_filtered,
                fromfile=f"{key} (aider)",
                tofile=f"{key} (litellm)",
                lineterm="",
                n=max(len(litellm_json_filtered), len(aider_json_filtered)),  # Show all lines
            )

            # Print the diff, skipping the header lines generated by unified_diff
            diff_lines = list(diff)[2:]
            if not diff_lines:
                # This case should ideally not be reached if dict comparison was done first,
                # but kept as a fallback.
                print(
                    "(No textual differences found, though dictionaries might differ in type/order)"
                )
            else:
                for line in diff_lines:
                    # Add color for better readability (optional, requires a library
                    # like 'termcolor' or manual ANSI codes)
                    # Simple +/- indication is standard for diffs
                    print(line)
            print("\n" + "=" * 40)

            # Ask user if they want to remove the entry from aider's metadata
            response = (
                input(f"Remove '{key}' from aider/resources/model-metadata.json? (y/N): ")
                .strip()
                .lower()
            )
            if response == "y":
                # Perform surgical removal from the text file
                if remove_block_surgically(aider_path, key):
                    removed_count += 1
                    # Optional: Also remove from the in-memory dict if needed later,
                    # but it's not strictly necessary if we reload or finish now.
                    # if key in aider_data: del aider_data[key]
                else:
                    print(f"Failed to remove '{key}' block surgically.")
                    # Key might still be in aider_data if removal failed
            else:
                print(f"Keeping '{key}'.")
            print("-" * 40 + "\n")  # Separator for the next model

    else:
        print("No common models found between the two files.")
        return  # Exit if no common keys

    # Final summary message
    if removed_count > 0:
        print(f"\nFinished comparing. A total of {removed_count} entr(y/ies) were removed.")
    else:
        print("\nFinished comparing. No entries were removed.")


if __name__ == "__main__":
    main()
