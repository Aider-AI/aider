import time

def _execute_remove(coder, file_path):
    """
    Explicitly remove a file from context.
    
    This allows the LLM to clean up its context when files are no
    longer needed, keeping the context focused and efficient.
    """
    try:
        # Get absolute path
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)

        # Check if file is in context (either editable or read-only)
        removed = False
        if abs_path in coder.abs_fnames:
            # Don't remove if it's the last editable file and there are no read-only files
            if len(coder.abs_fnames) <= 1 and not coder.abs_read_only_fnames:
                 coder.io.tool_output(f"⚠️ Cannot remove '{file_path}' - it's the only file in context")
                 return f"Cannot remove - last file in context"
            coder.abs_fnames.remove(abs_path)
            removed = True
        elif abs_path in coder.abs_read_only_fnames:
            # Don't remove if it's the last read-only file and there are no editable files
            if len(coder.abs_read_only_fnames) <= 1 and not coder.abs_fnames:
                 coder.io.tool_output(f"⚠️ Cannot remove '{file_path}' - it's the only file in context")
                 return f"Cannot remove - last file in context"
            coder.abs_read_only_fnames.remove(abs_path)
            removed = True

        if not removed:
            coder.io.tool_output(f"⚠️ File '{file_path}' not in context")
            return f"File not in context"

        # Track in recently removed
        coder.recently_removed[rel_path] = {
            'removed_at': time.time()
        }
        
        coder.io.tool_output(f"🗑️ Explicitly removed '{file_path}' from context")
        return f"Removed file from context"
    except Exception as e:
        coder.io.tool_error(f"Error removing file: {str(e)}")
        return f"Error: {str(e)}"
