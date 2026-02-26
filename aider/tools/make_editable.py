import os

# Keep the underscore prefix as this function is primarily for internal coder use
def _execute_make_editable(coder, file_path):
    """
    Convert a read-only file to an editable file.
    
    This allows the LLM to upgrade a file from read-only to editable
    when it determines it needs to make changes to that file.
    """
    try:
        # Get absolute path
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)
        
        # Check if file is already editable
        if abs_path in coder.abs_fnames:
            coder.io.tool_output(f"📝 File '{file_path}' is already editable")
            return f"File is already editable"

        # Check if file exists on disk
        if not os.path.isfile(abs_path):
            coder.io.tool_output(f"⚠️ File '{file_path}' not found")
            return f"Error: File not found"

        # File exists, is not editable, might be read-only or not in context yet
        was_read_only = False
        if abs_path in coder.abs_read_only_fnames:
            coder.abs_read_only_fnames.remove(abs_path)
            was_read_only = True

        # Add to editable files
        coder.abs_fnames.add(abs_path)

        if was_read_only:
            coder.io.tool_output(f"📝 Moved '{file_path}' from read-only to editable")
            return f"File is now editable (moved from read-only)"
        else:
            # File was not previously in context at all
            coder.io.tool_output(f"📝 Added '{file_path}' directly to editable context")
            # Track if added during exploration? Maybe not needed for direct MakeEditable.
            # coder.files_added_in_exploration.add(rel_path) # Consider if needed
            return f"File is now editable (added directly)"
    except Exception as e:
        coder.io.tool_error(f"Error in MakeEditable for '{file_path}': {str(e)}")
        return f"Error: {str(e)}"
