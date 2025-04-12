def _execute_make_readonly(coder, file_path):
    """
    Convert an editable file to a read-only file.
    
    This allows the LLM to downgrade a file from editable to read-only
    when it determines it no longer needs to make changes to that file.
    """
    try:
        # Get absolute path
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)
        
        # Check if file is in editable context
        if abs_path not in coder.abs_fnames:
            if abs_path in coder.abs_read_only_fnames:
                coder.io.tool_output(f"📚 File '{file_path}' is already read-only")
                return f"File is already read-only"
            else:
                coder.io.tool_output(f"⚠️ File '{file_path}' not in context")
                return f"File not in context"
        
        # Move from editable to read-only
        coder.abs_fnames.remove(abs_path)
        coder.abs_read_only_fnames.add(abs_path)
        
        coder.io.tool_output(f"📚 Made '{file_path}' read-only")
        return f"File is now read-only"
    except Exception as e:
        coder.io.tool_error(f"Error making file read-only: {str(e)}")
        return f"Error: {str(e)}"
