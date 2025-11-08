import os

from .tool_utils import (
    ToolError,
    apply_change,
    format_tool_result,
    generate_unified_diff_snippet,
    handle_tool_error,
)

schema = {
    "type": "function",
    "function": {
        "name": "DeleteLine",
        "description": "Delete a single line from a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "line_number": {"type": "integer"},
                "change_id": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["file_path", "line_number"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "deleteline"


def _execute_delete_line(coder, file_path, line_number, change_id=None, dry_run=False):
    """
    Delete a specific line number (1-based).

    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - line_number: The 1-based line number to delete
    - change_id: Optional ID for tracking the change
    - dry_run: If True, simulate the change without modifying the file

    Returns a result message.
    """

    tool_name = "DeleteLine"
    try:
        # Get absolute file path
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)

        # Check if file exists
        if not os.path.isfile(abs_path):
            raise ToolError(f"File '{file_path}' not found")

        # Check if file is in editable context
        if abs_path not in coder.abs_fnames:
            if abs_path in coder.abs_read_only_fnames:
                raise ToolError(f"File '{file_path}' is read-only. Use MakeEditable first.")
            else:
                raise ToolError(f"File '{file_path}' not in context")

        # Reread file content immediately before modification
        file_content = coder.io.read_text(abs_path)
        if file_content is None:
            raise ToolError(f"Could not read file '{file_path}'")

        lines = file_content.splitlines()
        original_content = file_content

        # Validate line number
        try:
            line_num_int = int(line_number)
            if line_num_int < 1 or line_num_int > len(lines):
                raise ToolError(f"Line number {line_num_int} is out of range (1-{len(lines)})")
            line_idx = line_num_int - 1  # Convert to 0-based index
        except ValueError:
            raise ToolError(f"Invalid line_number value: '{line_number}'. Must be an integer.")

        # Prepare the deletion
        deleted_line = lines[line_idx]
        new_lines = lines[:line_idx] + lines[line_idx + 1 :]
        new_content = "\n".join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(
                f"No changes made: deleting line {line_num_int} would not change file"
            )
            return f"Warning: No changes made (deleting line {line_num_int} would not change file)"

        # Generate diff snippet
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)

        # Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would delete line {line_num_int} in {file_path}"
            return format_tool_result(
                coder,
                tool_name,
                "",
                dry_run=True,
                dry_run_message=dry_run_message,
                diff_snippet=diff_snippet,
            )

        # --- Apply Change (Not dry run) ---
        metadata = {"line_number": line_num_int, "deleted_content": deleted_line}
        final_change_id = apply_change(
            coder,
            abs_path,
            rel_path,
            original_content,
            new_content,
            "deleteline",
            metadata,
            change_id,
        )

        coder.files_edited_by_tools.add(rel_path)

        # Format and return result
        success_message = f"Deleted line {line_num_int} in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        # Handle errors raised by utility functions (expected errors)
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)


def process_response(coder, params):
    """
    Process the DeleteLine tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    file_path = params.get("file_path")
    line_number = params.get("line_number")
    change_id = params.get("change_id")
    dry_run = params.get("dry_run", False)

    if file_path is not None and line_number is not None:
        return _execute_delete_line(coder, file_path, line_number, change_id, dry_run)
    else:
        return "Error: Missing required parameters for DeleteLine (file_path, line_number)"
