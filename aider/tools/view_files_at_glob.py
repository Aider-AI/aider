import fnmatch
import os

view_files_at_glob_schema = {
    "type": "function",
    "function": {
        "name": "ViewFilesAtGlob",
        "description": "View files matching a glob pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files.",
                },
            },
            "required": ["pattern"],
        },
    },
}


def execute_view_files_at_glob(coder, pattern):
    """
    Execute a glob pattern and return matching files as text.

    This tool helps the LLM find files by pattern matching, similar to
    how a developer would use glob patterns to find files.
    """
    try:
        # Find files matching the pattern
        matching_files = []

        # Make the pattern relative to root if it's absolute
        if pattern.startswith("/"):
            pattern = os.path.relpath(pattern, coder.root)

        # Get all files in the repo
        all_files = coder.get_all_relative_files()

        # Find matches with pattern matching
        for file in all_files:
            if fnmatch.fnmatch(file, pattern):
                matching_files.append(file)

        # Return formatted text instead of adding to context
        if matching_files:
            if len(matching_files) > 10:
                result = (
                    f"Found {len(matching_files)} files matching '{pattern}':"
                    f" {', '.join(matching_files[:10])} and {len(matching_files) - 10} more"
                )
                coder.io.tool_output(f"📂 Found {len(matching_files)} files matching '{pattern}'")
            else:
                result = (
                    f"Found {len(matching_files)} files matching '{pattern}':"
                    f" {', '.join(matching_files)}"
                )
                coder.io.tool_output(
                    f"📂 Found files matching '{pattern}':"
                    f" {', '.join(matching_files[:5])}{' and more' if len(matching_files) > 5 else ''}"
                )

            return result
        else:
            coder.io.tool_output(f"⚠️ No files found matching '{pattern}'")
            return f"No files found matching '{pattern}'"
    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesAtGlob: {str(e)}")
        return f"Error: {str(e)}"
