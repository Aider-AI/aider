import os
import traceback
from .tool_utils import generate_unified_diff_snippet
from .tool_utils import generate_unified_diff_snippet

def _execute_replace_lines(coder, file_path, start_line, end_line, new_content, change_id=None, dry_run=False):
    """
    Replace a range of lines identified by line numbers.
    Useful for fixing errors identified by error messages or linters.
    
    Parameters:
    - file_path: Path to the file to modify
    - start_line: The first line number to replace (1-based)
    - end_line: The last line number to replace (1-based)
    - new_content: New content for the lines (can be multi-line)
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
            coder.io.tool_error(f"Could not read file '{file_path}' before ReplaceLines operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Convert line numbers to integers if needed
        if not isinstance(start_line, int):
            try:
                start_line = int(start_line)
            except ValueError:
                coder.io.tool_error(f"Invalid start_line value: '{start_line}'. Must be an integer.")
                return f"Error: Invalid start_line value '{start_line}'"
        
        if not isinstance(end_line, int):
            try:
                end_line = int(end_line)
            except ValueError:
                coder.io.tool_error(f"Invalid end_line value: '{end_line}'. Must be an integer.")
                return f"Error: Invalid end_line value '{end_line}'"
        
        # Split into lines
        lines = file_content.splitlines()
        
        # Convert 1-based line numbers to 0-based indices
        start_idx = start_line - 1
        end_idx = end_line - 1
        # Validate line numbers
        if start_idx < 0 or start_idx >= len(lines):
            coder.io.tool_error(f"Start line {start_line} is out of range for file '{file_path}' (has {len(lines)} lines).")
            return f"Error: Start line {start_line} out of range"
         
        if end_idx < start_idx or end_idx >= len(lines):
            coder.io.tool_error(f"End line {end_line} is out of range for file '{file_path}' (must be >= start line {start_line} and <= {len(lines)}).")
            return f"Error: End line {end_line} out of range"
        
        # Store original content for change tracking
        original_content = file_content
        replaced_lines = lines[start_idx:end_idx+1]
        
        # Split the new content into lines
        new_lines = new_content.splitlines()
        
        # Perform the replacement
        new_full_lines = lines[:start_idx] + new_lines + lines[end_idx+1:]
        new_content_full = '\n'.join(new_full_lines)
        
        if original_content == new_content_full:
            coder.io.tool_warning("No changes made: new content is identical to original")
            return f"Warning: No changes made (new content identical to original)"
        diff_snippet = generate_unified_diff_snippet(original_content, new_content_full, rel_path)
         
        # Create a readable diff for the lines replacement
        diff = f"Lines {start_line}-{end_line}:\n"
        # Add removed lines with - prefix
        for line in replaced_lines:
            diff += f"- {line}\n"
        # Add separator
        diff += "---\n"
        # Add new lines with + prefix
        for line in new_lines:
            diff += f"+ {line}\n"

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would replace lines {start_line}-{end_line} in {file_path}")
            return f"Dry run: Would replace lines {start_line}-{end_line}. Diff snippet:\n{diff_snippet}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content_full)
         
        # Track the change
        try:
            metadata = {
                'start_line': start_line,
                'end_line': end_line,
                'replaced_lines': replaced_lines,
                'new_lines': new_lines
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='replacelines',
                original_content=original_content,
                new_content=new_content_full,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for ReplaceLines: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
        replaced_count = end_line - start_line + 1
        new_count = len(new_lines)
         
        # Improve feedback
        coder.io.tool_output(f"✅ Replaced lines {start_line}-{end_line} ({replaced_count} lines) with {new_count} new lines in {file_path} (change_id: {change_id})")
        return f"Successfully replaced lines {start_line}-{end_line} with {new_count} new lines (change_id: {change_id}). Diff:\n{diff}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in ReplaceLines: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"