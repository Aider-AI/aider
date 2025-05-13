import json
from pathlib import Path
import re

# Define file paths (assuming they are in the same directory as the script)
BASE_DIR = Path(__file__).resolve().parent
SESSION_DATA_FILE = BASE_DIR / "session.jsonl"

# Regex to identify common code/diff starting lines.
# This regex checks if the *first line* of a query starts with one of these patterns.
CODE_DIFF_MARKERS_REGEX = re.compile(
    r"^(```|diff --git|--- |\+\+\+ |@@ )"
)

def clean_query(query_text):
    """
    Cleans the query text.
    The cleaned query should be only the first line of the original query,
    and should not be a code/diff line itself.
    """
    if not isinstance(query_text, str) or not query_text.strip():
        # Return as is if not a string, or if it's an empty/whitespace-only string
        return query_text

    # First, get the part of the query before any "```diff" block
    query_before_diff = re.split(r"```diff", query_text, 1)[0]

    # If the part before "```diff" is empty or just whitespace, return empty string
    if not query_before_diff.strip():
        return ""

    # Now, take the first line of this potentially multi-line pre-diff query
    lines_before_diff = query_before_diff.splitlines()
    if not lines_before_diff: # Should be caught by query_before_diff.strip() check, but for safety
        return ""
    
    first_line = lines_before_diff[0]

    # Check if this first line itself is a code/diff marker
    if CODE_DIFF_MARKERS_REGEX.match(first_line):
        # If the first line itself is identified as a code/diff marker,
        # this implies the query might predominantly be code or a diff.
        # In this case, we set the query to an empty string.
        return ""
    else:
        # Otherwise, the first line is considered the cleaned query.
        return first_line

def main():
    """Main function to clean the query field in session.jsonl."""
    if not SESSION_DATA_FILE.exists():
        print(f"Error: Session data file not found at {SESSION_DATA_FILE}")
        return

    updated_lines = []
    modified_count = 0
    processed_lines = 0

    print(f"Starting cleaning process for {SESSION_DATA_FILE}...")

    with open(SESSION_DATA_FILE, "r", encoding="utf-8") as f:
        for line_num, line_content in enumerate(f, 1):
            processed_lines += 1
            try:
                data = json.loads(line_content)
                original_query = data.get("query") # Use .get() for safety

                if "query" in data and isinstance(original_query, str):
                    cleaned_query = clean_query(original_query)
                    if cleaned_query != original_query:
                        data["query"] = cleaned_query
                        modified_count += 1
                
                updated_lines.append(json.dumps(data) + "\n")

            except json.JSONDecodeError as e:
                print(f"Warning: Error decoding JSON from line {line_num}: {e}. Keeping original line.")
                updated_lines.append(line_content) # Keep original line if JSON error
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}. Keeping original line.")
                updated_lines.append(line_content) # Keep original line if other error

    # Write back to the original file
    try:
        with open(SESSION_DATA_FILE, "w", encoding="utf-8") as f:
            for updated_line in updated_lines:
                f.write(updated_line)
        print(f"\nProcessing complete.")
        print(f"Processed {processed_lines} lines.")
        print(f"{modified_count} queries were cleaned.")
        print(f"Cleaned data saved to {SESSION_DATA_FILE.resolve()}")
    except IOError as e:
        print(f"Error writing cleaned data to {SESSION_DATA_FILE}: {e}")


if __name__ == "__main__":
    main()
