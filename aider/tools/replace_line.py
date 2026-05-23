import os
import traceback

def _execute_replace_line(coder, file_path, line_number, new_content, change_id=None, dry_run=False):
    """
    Replace a specific line identified by line number.
    Useful for fixing errors identified by error messages or linters.
    
    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - line_number: The line number to replace (1-based)
    - new_content: New content for the line
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
            coder.io.tool_error(f"Could not read file '{file_path}' before ReplaceLine operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Split into lines
        lines = file_content.splitlines()
        
        # Validate line number
        if not isinstance(line_number, int):
            try:
                line_number = int(line_number)
            except ValueError:
                coder.io.tool_error(f"Line number must be an integer, got '{line_number}'")
                coder.io.tool_error(f"Invalid line_number value: '{line_number}'. Must be an integer.")
                return f"Error: Invalid line_number value '{line_number}'"
         
        # Convert 1-based line number to 0-based index
        idx = line_number - 1
         
        if idx < 0 or idx >= len(lines):
            coder.io.tool_error(f"Line number {line_number} is out of range for file '{file_path}' (has {len(lines)} lines).")
            return f"Error: Line number {line_number} out of range"
        
        # Store original content for change tracking
        original_content = file_content
        original_line = lines[idx]
        
        # Replace the line
        lines[idx] = new_content
        
        # Join lines back into a string
        new_content_full = '\n'.join(lines)
        
        if original_content == new_content_full:
            coder.io.tool_warning("No changes made: new line content is identical to original")
            return f"Warning: No changes made (new content identical to original)"
         
        # Create a readable diff for the line replacement
        diff = f"Line {line_number}:\n- {original_line}\n+ {new_content}"

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would replace line {line_number} in {file_path}")
            return f"Dry run: Would replace line {line_number}. Diff:\n{diff}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content_full)
         
        # Track the change
        try:
            metadata = {
                'line_number': line_number,
                'original_line': original_line,
                'new_line': new_content
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='replaceline',
                original_content=original_content,
                new_content=new_content_full,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for ReplaceLine: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
         
        # Improve feedback
        coder.io.tool_output(f"✅ Replaced line {line_number} in {file_path} (change_id: {change_id})")
        return f"Successfully replaced line {line_number} (change_id: {change_id}). Diff:\n{diff}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in ReplaceLine: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
