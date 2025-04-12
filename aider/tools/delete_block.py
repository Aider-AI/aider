import os
import traceback

def _execute_delete_block(coder, file_path, start_pattern, end_pattern=None, line_count=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Delete a block of text between start_pattern and end_pattern (inclusive).
    
    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - start_pattern: Pattern marking the start of the block to delete (line containing this pattern)
    - end_pattern: Optional pattern marking the end of the block (line containing this pattern)
    - line_count: Optional number of lines to delete (alternative to end_pattern)
    - near_context: Optional text nearby to help locate the correct instance of the start_pattern
    - occurrence: Which occurrence of the start_pattern to use (1-based index, or -1 for last)
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
            coder.io.tool_error(f"Could not read file '{file_path}' before DeleteBlock operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Validate we have either end_pattern or line_count, but not both
        if end_pattern and line_count:
            coder.io.tool_error("Cannot specify both end_pattern and line_count")
            return "Error: Cannot specify both end_pattern and line_count"
        
        # Split into lines for easier handling
        lines = file_content.splitlines()
        original_content = file_content
         
        # Find occurrences of the start_pattern
        start_pattern_line_indices = []
        for i, line in enumerate(lines):
            if start_pattern in line:
                if near_context:
                    context_window_start = max(0, i - 5)
                    context_window_end = min(len(lines), i + 6)
                    context_block = "\n".join(lines[context_window_start:context_window_end])
                    if near_context in context_block:
                        start_pattern_line_indices.append(i)
                else:
                    start_pattern_line_indices.append(i)

        if not start_pattern_line_indices:
            err_msg = f"Start pattern '{start_pattern}' not found"
            if near_context: err_msg += f" near context '{near_context}'"
            err_msg += f" in file '{file_path}'."
            coder.io.tool_error(err_msg)
            return f"Error: {err_msg}"

        # Select the occurrence for the start pattern
        num_occurrences = len(start_pattern_line_indices)
        try:
            occurrence = int(occurrence)
            if occurrence == -1:
                target_idx = num_occurrences - 1
            elif occurrence > 0 and occurrence <= num_occurrences:
                target_idx = occurrence - 1
            else:
                err_msg = f"Occurrence number {occurrence} is out of range for start pattern '{start_pattern}'. Found {num_occurrences} occurrences"
                if near_context: err_msg += f" near '{near_context}'"
                err_msg += f" in '{file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}"
        except ValueError:
            coder.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
            return f"Error: Invalid occurrence value '{occurrence}'"

        start_line = start_pattern_line_indices[target_idx]
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
        
        # Find the end line based on end_pattern or line_count
        end_line = -1
        if end_pattern:
            for i in range(start_line, len(lines)):
                if end_pattern in lines[i]:
                    end_line = i
                    break
            if end_line == -1:
                err_msg = f"End pattern '{end_pattern}' not found after {occurrence_str}start pattern '{start_pattern}' (line {start_line + 1}) in '{file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}"
        elif line_count:
            try:
                line_count = int(line_count)
                if line_count <= 0: raise ValueError("Line count must be positive")
                end_line = min(start_line + line_count - 1, len(lines) - 1)
            except ValueError:
                coder.io.tool_error(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
                return f"Error: Invalid line_count value '{line_count}'"
        else:
            end_line = start_line
            
        # Prepare the deletion
        deleted_lines = lines[start_line:end_line+1]
        new_lines = lines[:start_line] + lines[end_line+1:]
        new_content = '\n'.join(new_lines)
         
        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: deletion would not change file")
            return f"Warning: No changes made (deletion would not change file)"

        # Generate diff for feedback (assuming _generate_diff_snippet_delete is available on coder)
        diff_snippet = coder._generate_diff_snippet_delete(original_content, start_line, end_line)

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would delete lines {start_line+1}-{end_line+1} (based on {occurrence_str}start pattern '{start_pattern}') in {file_path}")
            return f"Dry run: Would delete block. Diff snippet:\n{diff_snippet}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)
         
        # Track the change
        try:
            metadata = {
                'start_line': start_line + 1,
                'end_line': end_line + 1,
                'start_pattern': start_pattern,
                'end_pattern': end_pattern,
                'line_count': line_count,
                'near_context': near_context,
                'occurrence': occurrence,
                'deleted_content': '\n'.join(deleted_lines)
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='deleteblock',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for DeleteBlock: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
         
        # Improve feedback
        num_deleted = end_line - start_line + 1
        coder.io.tool_output(f"✅ Deleted {num_deleted} lines (from {occurrence_str}start pattern) in {file_path} (change_id: {change_id})")
        return f"Successfully deleted {num_deleted} lines (change_id: {change_id}). Diff snippet:\n{diff_snippet}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in DeleteBlock: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
