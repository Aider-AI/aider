import shlex
import shutil
from pathlib import Path
from aider.run_cmd import run_cmd_subprocess

def _find_search_tool():
    """Find the best available command-line search tool (rg, ag, grep)."""
    if shutil.which('rg'):
        return 'rg', shutil.which('rg')
    elif shutil.which('ag'):
        return 'ag', shutil.which('ag')
    elif shutil.which('grep'):
        return 'grep', shutil.which('grep')
    else:
        return None, None

def _execute_grep(coder, pattern, file_pattern="*", directory=".", use_regex=False, case_insensitive=False, context_before=5, context_after=5):
    """
    Search for lines matching a pattern in files within the project repository.
    Uses rg (ripgrep), ag (the silver searcher), or grep, whichever is available.

    Args:
        coder: The Coder instance.
        pattern (str): The pattern to search for.
        file_pattern (str, optional): Glob pattern to filter files. Defaults to "*".
        directory (str, optional): Directory to search within relative to repo root. Defaults to ".".
        use_regex (bool, optional): Whether the pattern is a regular expression. Defaults to False.
        case_insensitive (bool, optional): Whether the search should be case-insensitive. Defaults to False.
        context_before (int, optional): Number of context lines to show before matches. Defaults to 5.
        context_after (int, optional): Number of context lines to show after matches. Defaults to 5.

    Returns:
        str: Formatted result indicating success or failure, including matching lines or error message.
    """
    repo = coder.repo
    if not repo:
        coder.io.tool_error("Not in a git repository.")
        return "Error: Not in a git repository."

    tool_name, tool_path = _find_search_tool()
    if not tool_path:
        coder.io.tool_error("No search tool (rg, ag, grep) found in PATH.")
        return "Error: No search tool (rg, ag, grep) found."

    try:
        search_dir_path = Path(repo.root) / directory
        if not search_dir_path.is_dir():
            coder.io.tool_error(f"Directory not found: {directory}")
            return f"Error: Directory not found: {directory}"

        # Build the command arguments based on the available tool
        cmd_args = [tool_path]

        # Common options or tool-specific equivalents
        if tool_name in ['rg', 'grep']:
            cmd_args.append("-n")  # Line numbers for rg and grep
        # ag includes line numbers by default

        # Context lines (Before and After)
        if context_before > 0:
            # All tools use -B for lines before
            cmd_args.extend(["-B", str(context_before)])
        if context_after > 0:
            # All tools use -A for lines after
            cmd_args.extend(["-A", str(context_after)])

        # Case sensitivity
        if case_insensitive:
            cmd_args.append("-i") # Add case-insensitivity flag for all tools

        # Pattern type (regex vs fixed string)
        if use_regex:
            if tool_name == 'grep':
                cmd_args.append("-E") # Use extended regex for grep
            # rg and ag use regex by default, no flag needed for basic ERE
        else:
            if tool_name == 'rg':
                cmd_args.append("-F") # Fixed strings for rg
            elif tool_name == 'ag':
                cmd_args.append("-Q") # Literal/fixed strings for ag
            elif tool_name == 'grep':
                cmd_args.append("-F") # Fixed strings for grep

        # File filtering
        if file_pattern != "*": # Avoid adding glob if it's the default '*' which might behave differently
            if tool_name == 'rg':
                cmd_args.extend(["-g", file_pattern])
            elif tool_name == 'ag':
                cmd_args.extend(["-G", file_pattern])
            elif tool_name == 'grep':
                # grep needs recursive flag when filtering
                cmd_args.append("-r")
                cmd_args.append(f"--include={file_pattern}")
        elif tool_name == 'grep':
             # grep needs recursive flag even without include filter
             cmd_args.append("-r")

        # Directory exclusion (rg and ag respect .gitignore/.git by default)
        if tool_name == 'grep':
            cmd_args.append("--exclude-dir=.git")

        # Add pattern and directory path
        cmd_args.extend([pattern, str(search_dir_path)])

        # Convert list to command string for run_cmd_subprocess
        command_string = shlex.join(cmd_args)

        coder.io.tool_output(f"⚙️ Executing {tool_name}: {command_string}")

        # Use run_cmd_subprocess for execution
        # Note: rg, ag, and grep return 1 if no matches are found, which is not an error for this tool.
        exit_status, combined_output = run_cmd_subprocess(
            command_string,
            verbose=coder.verbose,
            cwd=coder.root # Execute in the project root
        )

        # Format the output for the result message
        output_content = combined_output or ""

        # Handle exit codes (consistent across rg, ag, grep)
        if exit_status == 0:
            # Limit output size if necessary
            max_output_lines = 50 # Consider making this configurable
            output_lines = output_content.splitlines()
            if len(output_lines) > max_output_lines:
                truncated_output = "\n".join(output_lines[:max_output_lines])
                result_message = f"Found matches (truncated):\n```text\n{truncated_output}\n... ({len(output_lines) - max_output_lines} more lines)\n```"
            elif not output_content:
                 # Should not happen if return code is 0, but handle defensively
                 coder.io.tool_warning(f"{tool_name} returned 0 but produced no output.")
                 result_message = "No matches found (unexpected)."
            else:
                result_message = f"Found matches:\n```text\n{output_content}\n```"
            return result_message

        elif exit_status == 1:
            # Exit code 1 means no matches found - this is expected behavior, not an error.
            return "No matches found."
        else:
            # Exit code > 1 indicates an actual error
            error_message = f"{tool_name.capitalize()} command failed with exit code {exit_status}."
            if output_content:
                # Truncate error output as well if it's too long
                error_limit = 1000 # Example limit for error output
                if len(output_content) > error_limit:
                    output_content = output_content[:error_limit] + "\n... (error output truncated)"
                error_message += f" Output:\n{output_content}"
            coder.io.tool_error(error_message)
            return f"Error: {error_message}"

    except Exception as e:
        # Add command_string to the error message if it's defined
        cmd_str_info = f"'{command_string}' " if 'command_string' in locals() else ""
        coder.io.tool_error(f"Error executing {tool_name} command {cmd_str_info}: {str(e)}")
        return f"Error executing {tool_name}: {str(e)}"
