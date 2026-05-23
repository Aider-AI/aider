import traceback

def _execute_undo_change(coder, change_id=None, file_path=None): 
    """
    Undo a specific change by ID, or the last change to a file.
     
    Parameters:
    - coder: The Coder instance
    - change_id: ID of the change to undo
    - file_path: Path to file where the last change should be undone
     
    Returns a result message.
    """
    # Note: Undo does not have a dry_run parameter as it's inherently about reverting a previous action.
    try:
        # Validate parameters
        if change_id is None and file_path is None:
            coder.io.tool_error("Must specify either change_id or file_path for UndoChange")
            return "Error: Must specify either change_id or file_path"
         
        # If file_path is specified, get the most recent change for that file
        if file_path: 
            abs_path = coder.abs_root_path(file_path)
            rel_path = coder.get_rel_fname(abs_path)
              
            change_id = coder.change_tracker.get_last_change(rel_path)
            if not change_id:
                coder.io.tool_error(f"No tracked changes found for file '{file_path}' to undo.")
                return f"Error: No changes found for file '{file_path}'"
        
        # Attempt to get undo information from the tracker
        success, message, change_info = coder.change_tracker.undo_change(change_id)
          
        if not success:
            coder.io.tool_error(f"Failed to undo change '{change_id}': {message}")
            return f"Error: {message}"
        
        # Apply the undo by restoring the original content
        if change_info:
            file_path = change_info['file_path']
            abs_path = coder.abs_root_path(file_path)
            # Write the original content back to the file
            coder.io.write_text(abs_path, change_info['original'])
            coder.aider_edited_files.add(file_path) # Track that the file was modified by the undo
             
            change_type = change_info['type']
            coder.io.tool_output(f"✅ Undid {change_type} change '{change_id}' in {file_path}")
            return f"Successfully undid {change_type} change '{change_id}'."
        else:
            # This case should ideally not be reached if tracker returns success
            coder.io.tool_error(f"Failed to undo change '{change_id}': Change info missing after successful tracker update.")
            return f"Error: Failed to undo change '{change_id}' (missing change info)"
             
    except Exception as e:
        coder.io.tool_error(f"Error in UndoChange: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"
