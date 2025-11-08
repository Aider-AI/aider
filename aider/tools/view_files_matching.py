import fnmatch
import re

schema = {
    "type": "function",
    "function": {
        "name": "ViewFilesMatching",
        "description": "View files containing a specific pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The pattern to search for in file contents.",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "An optional glob pattern to filter which files are searched.",
                },
                "regex": {
                    "type": "boolean",
                    "description": (
                        "Whether the pattern is a regular expression. Defaults to False."
                    ),
                },
            },
            "required": ["pattern"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "viewfilesmatching"


def execute_view_files_matching(coder, pattern, file_pattern=None, regex=False):
    """
    Search for pattern (literal string or regex) in files and return matching files as text.

    Args:
        coder: The Coder instance.
        pattern (str): The pattern to search for.
            Treated as a literal string by default.
        file_pattern (str, optional): Glob pattern to filter which files are searched.
            Defaults to None (search all files).
        regex (bool, optional): If True, treat pattern as a regular expression.
            Defaults to False.

    This tool lets the LLM search for content within files, mimicking
    how a developer would use grep or regex search to find relevant code.
    """
    try:
        # Get list of files to search
        if file_pattern:
            # Use glob pattern to filter files
            all_files = coder.get_all_relative_files()
            files_to_search = []
            for file in all_files:
                if fnmatch.fnmatch(file, file_pattern):
                    files_to_search.append(file)

            if not files_to_search:
                return f"No files matching '{file_pattern}' to search for pattern '{pattern}'"
        else:
            # Search all files if no pattern provided
            files_to_search = coder.get_all_relative_files()

        # Search for pattern in files
        matches = {}
        for file in files_to_search:
            abs_path = coder.abs_root_path(file)
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    match_count = 0
                    if regex:
                        try:
                            matches_found = re.findall(pattern, content)
                            match_count = len(matches_found)
                        except re.error as e:
                            # Handle invalid regex patterns gracefully
                            coder.io.tool_error(f"Invalid regex pattern '{pattern}': {e}")
                            # Skip this file for this search if regex is invalid
                            continue
                    else:
                        # Exact string matching
                        match_count = content.count(pattern)

                    if match_count > 0:
                        matches[file] = match_count
            except Exception:
                # Skip files that can't be read (binary, etc.)
                pass

        # Return formatted text instead of adding to context
        if matches:
            # Sort by number of matches (most matches first)
            sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
            match_list = [f"{file} ({count} matches)" for file, count in sorted_matches]

            if len(matches) > 10:
                result = (
                    f"Found '{pattern}' in {len(matches)} files: {', '.join(match_list[:10])} and"
                    f" {len(matches) - 10} more"
                )
                coder.io.tool_output(f"🔍 Found '{pattern}' in {len(matches)} files")
            else:
                result = f"Found '{pattern}' in {len(matches)} files: {', '.join(match_list)}"
                coder.io.tool_output(
                    f"🔍 Found '{pattern}' in:"
                    f" {', '.join(match_list[:5])}{' and more' if len(matches) > 5 else ''}"
                )

            return result
        else:
            coder.io.tool_output(f"⚠️ Pattern '{pattern}' not found in any files")
            return "Pattern not found in any files"
    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesMatching: {str(e)}")
        return f"Error: {str(e)}"


def process_response(coder, params):
    """
    Process the ViewFilesMatching tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    pattern = params.get("pattern")
    file_pattern = params.get("file_pattern")
    regex = params.get("regex", False)

    if pattern is not None:
        return execute_view_files_matching(coder, pattern, file_pattern, regex)
    else:
        return "Error: Missing 'pattern' parameter for ViewFilesMatching"
