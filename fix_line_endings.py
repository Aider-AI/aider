import sys

def fix_line_endings(file_path):
    """
    Converts the line endings of a file from CRLF to LF.
    """
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            content = f.read()

        with open(file_path, 'w', newline='\n', encoding='utf-8') as f:
            f.write(content)

        print(f"Successfully converted line endings for: {file_path}")

    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_line_endings.py <file_path>", file=sys.stderr)
        sys.exit(1)
    
    file_to_fix = sys.argv[1]
    fix_line_endings(file_to_fix)
