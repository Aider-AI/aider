import os
import traceback

def _execute_insert_block(coder, file_path, content, after_pattern=None, before_pattern=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Insert a block of text after or before a specified pattern.
    
    Parameters:
    - coder: The Coder instance
    - file_path: Path to the file to modify
    - content: Text block to insert
    - after_pattern: Pattern after which to insert the block (line containing this pattern) - specify one of after/before
    - before_pattern: Pattern before which to insert the block (line containing this pattern) - specify one of after/before
    - near_context: Optional text nearby to help locate the correct instance of the pattern
    - occurrence: Which occurrence of the pattern to use (1-based index, or -1 for last)
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
         
        # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
        file_content = coder.io.read_text(abs_path)
        if file_content is None:
            # Provide more specific error (Improves Point 4)
            coder.io.tool_error(f"Could not read file '{file_path}' before InsertBlock operation.")
            return f"Error: Could not read file '{file_path}'"
        
        # Validate we have either after_pattern or before_pattern, but not both
        if after_pattern and before_pattern:
            coder.io.tool_error("Cannot specify both after_pattern and before_pattern")
            return "Error: Cannot specify both after_pattern and before_pattern"
        if not after_pattern and not before_pattern:
            coder.io.tool_error("Must specify either after_pattern or before_pattern")
            return "Error: Must specify either after_pattern or before_pattern"
        
        # Split into lines for easier handling
        lines = file_content.splitlines()
        original_content = file_content
         
        # Find occurrences of the pattern (either after_pattern or before_pattern)
        pattern = after_pattern if after_pattern else before_pattern
        pattern_type = "after" if after_pattern else "before"
         
        # Find line indices containing the pattern
        pattern_line_indices = []
        for i, line in enumerate(lines):
            if pattern in line:
                # If near_context is provided, check if it's nearby
                if near_context:
                    context_window_start = max(0, i - 5) # Check 5 lines before/after
                    context_window_end = min(len(lines), i + 6)
                    context_block = "\n".join(lines[context_window_start:context_window_end])
                    if near_context in context_block:
                        pattern_line_indices.append(i)
                else:
                    pattern_line_indices.append(i)

        if not pattern_line_indices:
            err_msg = f"Pattern '{pattern}' not found"
            if near_context: err_msg += f" near context '{near_context}'"
            err_msg += f" in file '{file_path}'."
            coder.io.tool_error(err_msg)
            return f"Error: {err_msg}" # Improve Point 4

        # Select the occurrence (Implements Point 5)
        num_occurrences = len(pattern_line_indices)
        try:
            occurrence = int(occurrence) # Ensure occurrence is an integer
            if occurrence == -1: # Last occurrence
                target_idx = num_occurrences - 1
            elif occurrence > 0 and occurrence <= num_occurrences:
                target_idx = occurrence - 1 # Convert 1-based to 0-based
            else:
                err_msg = f"Occurrence number {occurrence} is out of range for pattern '{pattern}'. Found {num_occurrences} occurrences"
                if near_context: err_msg += f" near '{near_context}'"
                err_msg += f" in '{file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}" # Improve Point 4
        except ValueError:
            coder.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
            return f"Error: Invalid occurrence value '{occurrence}'"

        # Determine the final insertion line index
        insertion_line_idx = pattern_line_indices[target_idx]
        if pattern_type == "after":
            insertion_line_idx += 1 # Insert on the line *after* the matched line
        # Prepare the content to insert
        content_lines = content.splitlines()
         
        # Create the new lines array
        new_lines = lines[:insertion_line_idx] + content_lines + lines[insertion_line_idx:]
        new_content = '\n'.join(new_lines) # Use '\n' to match io.write_text behavior
         
        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: insertion would not change file")
            return f"Warning: No changes made (insertion would not change file)"

        # Generate diff for feedback
        diff_snippet = coder._generate_diff_snippet_insert(original_content, insertion_line_idx, content_lines)

        # Handle dry run (Implements Point 6)
        if dry_run:
            occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
            coder.io.tool_output(f"Dry run: Would insert block {pattern_type} {occurrence_str}pattern '{pattern}' in {file_path}")
            return f"Dry run: Would insert block. Diff snippet:\n{diff_snippet}"

        # --- Apply Change (Not dry run) ---
        coder.io.write_text(abs_path, new_content)
         
        # Track the change
        try:
            metadata = {
                'insertion_line_idx': insertion_line_idx,
                'after_pattern': after_pattern,
                'before_pattern': before_pattern,
                'near_context': near_context,
                'occurrence': occurrence,
                'content': content
            }
            change_id = coder.change_tracker.track_change(
                file_path=rel_path,
                change_type='insertblock',
                original_content=original_content,
                new_content=new_content,
                metadata=metadata,
                change_id=change_id
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking change for InsertBlock: {track_e}")
            change_id = "TRACKING_FAILED"

        coder.aider_edited_files.add(rel_path)
         
        # Improve feedback (Point 5 & 6)
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
        coder.io.tool_output(f"✅ Inserted block {pattern_type} {occurrence_str}pattern in {file_path} (change_id: {change_id})")
        return f"Successfully inserted block (change_id: {change_id}). Diff snippet:\n{diff_snippet}"
             
    except Exception as e:
        coder.io.tool_error(f"Error in InsertBlock: {str(e)}\n{traceback.format_exc()}") # Add traceback
        return f"Error: {str(e)}"