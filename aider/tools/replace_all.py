import os
import traceback

def _execute_replace_all(coder, file_path, find_text, replace_text, change_id=None, dry_run=False):
    """
    Replace all occurrences of text in a file.
    
    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - find_text: Text to find and replace
    - replace_text: Text to replace it with
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
        content = coder.io.read_text(abs_path)
        if content is None:
            coder.io.tool_error(f"Could not read file '{file_path}' before ReplaceAll operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Count occurrences
        count = content.count(find_text)
        if count == 0:
            coder.io.tool_warning(f"Text '{find_text}' not found in file")
            return f"Warning: Text not found in file"
        
        # Perform the replacement
        original_content = content
        new_content = content.replace(find_text, replace_text)
        
        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: replacement text is identical to original")
            return f"Warning: No changes made (replacement identical to original)"
         
        # Generate diff for feedback (more comprehensive for ReplaceAll)
        diff_examples = coder._generate_diff_chunks(original_content, find_text, replace_text)

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would replace {count} occurrences of '{find_text}' in {file_path}")
            return f"Dry run: Would replace {count} occurrences. Diff examples:\n{diff_examples}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)
         
        # Track the change
        try:
            metadata = {
                'find_text': find_text,
                'replace_text': replace_text,
                'occurrences': count
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='replaceall',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for ReplaceAll: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
         
        # Improve feedback
        coder.io.tool_output(f"✅ Replaced {count} occurrences in {file_path} (change_id: {change_id})")
        return f"Successfully replaced {count} occurrences (change_id: {change_id}). Diff examples:\n{diff_examples}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in ReplaceAll: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
