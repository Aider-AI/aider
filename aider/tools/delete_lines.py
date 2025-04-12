import os
import traceback

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
            coder.io.tool_error(f"Could not read file '{file_path}' before DeleteLines operation.")
            return f"Error: Could not read file '{file_path}'"

        lines = file_content.splitlines()
        original_content = file_content

        # Validate line numbers
        try:
            start_line_int = int(start_line)
            end_line_int = int(end_line)

            if start_line_int < 1 or start_line_int > len(lines):
                raise ValueError(f"Start line {start_line_int} is out of range (1-{len(lines)})")
            if end_line_int < 1 or end_line_int > len(lines):
                raise ValueError(f"End line {end_line_int} is out of range (1-{len(lines)})")
            if start_line_int > end_line_int:
                raise ValueError(f"Start line {start_line_int} cannot be after end line {end_line_int}")

            start_idx = start_line_int - 1 # Convert to 0-based index
            end_idx = end_line_int - 1   # Convert to 0-based index
        except ValueError as e:
            coder.io.tool_error(f"Invalid line numbers: {e}")
            return f"Error: Invalid line numbers '{start_line}', '{end_line}'"

        # Prepare the deletion
        deleted_lines = lines[start_idx:end_idx+1]
        new_lines = lines[:start_idx] + lines[end_idx+1:]
        new_content = '\n'.join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: deleting lines {start_line_int}-{end_line_int} would not change file")
            return f"Warning: No changes made (deleting lines {start_line_int}-{end_line_int} would not change file)"

        # Generate diff snippet
        diff_snippet = coder._generate_diff_snippet_delete(original_content, start_idx, end_idx)

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would delete lines {start_line_int}-{end_line_int} in {file_path}")
            return f"Dry run: Would delete lines {start_line_int}-{end_line_int}. Diff snippet:\n{diff_snippet}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)

        # Track the change
        try:
            metadata = {
                'start_line': start_line_int,
                'end_line': end_line_int,
                'deleted_content': '\n'.join(deleted_lines)
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='deletelines',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for DeleteLines: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)

        num_deleted = end_idx - start_idx + 1
        coder.io.tool_output(f"✅ Deleted {num_deleted} lines ({start_line_int}-{end_line_int}) in {file_path} (change_id: {change_id})")
        return f"Successfully deleted {num_deleted} lines ({start_line_int}-{end_line_int}) (change_id: {change_id}). Diff snippet:\n{diff_snippet}"

    except Exception as e:
        coder.io.tool_error(f"Error in DeleteLines: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
