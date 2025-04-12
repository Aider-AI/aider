import os
import traceback

def _execute_replace_text(coder, file_path, find_text, replace_text, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Replace specific text with new text, optionally using nearby context for disambiguation.
    
    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - find_text: Text to find and replace
    - replace_text: Text to replace it with
    - near_context: Optional text nearby to help locate the correct instance
    - occurrence: Which occurrence to replace (1-based index, or -1 for last)
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
            coder.io.tool_error(f"Could not read file '{file_path}' before ReplaceText operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Find occurrences using helper function (assuming _find_occurrences is available on coder)
        occurrences = coder._find_occurrences(content, find_text, near_context)
         
        if not occurrences:
            err_msg = f"Text '{find_text}' not found"
            if near_context:
                err_msg += f" near context '{near_context}'"
            err_msg += f" in file '{file_path}'."
            coder.io.tool_error(err_msg)
            return f"Error: {err_msg}"

        # Select the occurrence
        num_occurrences = len(occurrences)
        try:
            occurrence = int(occurrence)
            if occurrence == -1:
                target_idx = num_occurrences - 1
            elif occurrence > 0 and occurrence <= num_occurrences:
                target_idx = occurrence - 1
            else:
                err_msg = f"Occurrence number {occurrence} is out of range. Found {num_occurrences} occurrences of '{find_text}'"
                if near_context: err_msg += f" near '{near_context}'"
                err_msg += f" in '{file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}"
        except ValueError:
            coder.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
            return f"Error: Invalid occurrence value '{occurrence}'"

        start_index = occurrences[target_idx]
        
        # Perform the replacement
        original_content = content
        new_content = content[:start_index] + replace_text + content[start_index + len(find_text):]
        
        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: replacement text is identical to original")
            return f"Warning: No changes made (replacement identical to original)"
         
        # Generate diff for feedback (assuming _generate_diff_snippet is available on coder)
        diff_example = coder._generate_diff_snippet(original_content, start_index, len(find_text), replace_text)

        # Handle dry run
        if dry_run:
            coder.io.tool_output(f"Dry run: Would replace occurrence {occurrence} of '{find_text}' in {file_path}")
            return f"Dry run: Would replace text (occurrence {occurrence}). Diff snippet:\n{diff_example}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)
         
        # Track the change
        try:
            metadata = {
                'start_index': start_index,
                'find_text': find_text,
                'replace_text': replace_text,
                'near_context': near_context,
                'occurrence': occurrence
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='replacetext',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for ReplaceText: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
         
        # Improve feedback
        occurrence_str = f"occurrence {occurrence}" if num_occurrences > 1 else "text"
        coder.io.tool_output(f"✅ Replaced {occurrence_str} in {file_path} (change_id: {change_id})")
        return f"Successfully replaced {occurrence_str} (change_id: {change_id}). Diff snippet:\n{diff_example}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in ReplaceText: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
