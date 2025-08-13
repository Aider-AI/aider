import os
import traceback
from .tool_utils import ToolError, generate_unified_diff_snippet, handle_tool_error, format_tool_result, apply_change

def _execute_delete_lines(coder, file_path, start_line, end_line, change_id=None, dry_run=False):
    """
    Delete a range of lines (1-based, inclusive).

    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - start_line: The 1-based starting line number to delete
    - end_line: The 1-based ending line number to delete
    - change_id: Optional ID for tracking the change
    - dry_run: If True, simulate the change without modifying the file

    Returns a result message.
    """
    tool_name = "DeleteLines"
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

        # Validate line numbers
        try:
            start_line_int = int(start_line)
            end_line_int = int(end_line)

            if start_line_int < 1 or start_line_int > len(lines):
                raise ToolError(f"Start line {start_line_int} is out of range (1-{len(lines)})")
            if end_line_int < 1 or end_line_int > len(lines):
                raise ToolError(f"End line {end_line_int} is out of range (1-{len(lines)})")
            if start_line_int > end_line_int:
                raise ToolError(f"Start line {start_line_int} cannot be after end line {end_line_int}")

            start_idx = start_line_int - 1 # Convert to 0-based index
            end_idx = end_line_int - 1   # Convert to 0-based index
        except ValueError:
            raise ToolError(f"Invalid line numbers: '{start_line}', '{end_line}'. Must be integers.")

        # Prepare the deletion
        deleted_lines = lines[start_idx:end_idx+1]
        new_lines = lines[:start_idx] + lines[end_idx+1:]
        new_content = '\n'.join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: deleting lines {start_line_int}-{end_line_int} would not change file")
            return f"Warning: No changes made (deleting lines {start_line_int}-{end_line_int} would not change file)"

        # Generate diff snippet
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)

        # Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would delete lines {start_line_int}-{end_line_int} in {file_path}"
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_snippet)

        # --- Apply Change (Not dry run) ---
        metadata = {
            'start_line': start_line_int,
            'end_line': end_line_int,
            'deleted_content': '\n'.join(deleted_lines)
        }
        
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'deletelines', metadata, change_id
        )

        coder.aider_edited_files.add(rel_path)
        num_deleted = end_idx - start_idx + 1
        # Format and return result
        success_message = f"Deleted {num_deleted} lines ({start_line_int}-{end_line_int}) in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        # Handle errors raised by utility functions (expected errors)
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)