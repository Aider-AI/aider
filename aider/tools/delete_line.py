import os
import traceback

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
    try:
        # Get absolute file path
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)

        # Check if file exists
        if not os.path.isfile(abs_path):
            coder.io.tool_error(f"File '{file_path}' not found")
            return f"Error: File not found"

        # Check if file is in editable context
        if abs_path not in coder.abs_fnames:
            if abs_path in coder.abs_read_only_fnames:
                coder.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                return f"Error: File is read-only. Use MakeEditable first."
            else:
                coder.io.tool_error(f"File '{file_path}' not in context")
                return f"Error: File not in context"

        # Reread file content immediately before modification
        file_content = coder.io.read_text(abs_path)
        if file_content is None:
            coder.io.tool_error(f"Could not read file '{file_path}' before DeleteLine operation.")
            return f"Error: Could not read file '{file_path}'"

        lines = file_content.splitlines()
        original_content = file_content

        # Validate line number
        try:
            line_num_int = int(line_number)
            if line_num_int < 1 or line_num_int > len(lines):
                raise ValueError(f"Line number {line_num_int} is out of range (1-{len(lines)})")
            line_idx = line_num_int - 1 # Convert to 0-based index
        except ValueError as e:
            coder.io.tool_error(f"Invalid line_number: {e}")
            return f"Error: Invalid line_number '{line_number}'"

        # Prepare the deletion
        deleted_line = lines[line_idx]
        new_lines = lines[:line_idx] + lines[line_idx+1:]
        new_content = '\n'.join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: deleting line {line_num_int} would not change file")
            return f"Warning: No changes made (deleting line {line_num_int} would not change file)"

        # Generate diff snippet (using the existing delete block helper for simplicity)
        diff_snippet = coder._generate_diff_snippet_delete(original_content, line_idx, line_idx)

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would delete line {line_num_int} in {file_path}")
            return f"Dry run: Would delete line {line_num_int}. Diff snippet:\n{diff_snippet}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)

        # Track the change
        try:
            metadata = {
                'line_number': line_num_int,
                'deleted_content': deleted_line
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='deleteline',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for DeleteLine: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)

        coder.io.tool_output(f"✅ Deleted line {line_num_int} in {file_path} (change_id: {change_id})")
        return f"Successfully deleted line {line_num_int} (change_id: {change_id}). Diff snippet:\n{diff_snippet}"

    except Exception as e:
        coder.io.tool_error(f"Error in DeleteLine: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
