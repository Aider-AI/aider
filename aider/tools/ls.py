import os

def execute_ls(coder, dir_path):
    """
    List files in directory and optionally add some to context.
    
    This provides information about the structure of the codebase,
    similar to how a developer would explore directories.
    """
    try:
        # Make the path relative to root if it's absolute
        if dir_path.startswith('/'):
            rel_dir = os.path.relpath(dir_path, coder.root)
        else:
            rel_dir = dir_path
        
        # Get absolute path
        abs_dir = coder.abs_root_path(rel_dir)
        
        # Check if path exists
        if not os.path.exists(abs_dir):
            coder.io.tool_output(f"⚠️ Directory '{dir_path}' not found")
            return f"Directory not found"
        
        # Get directory contents
        contents = []
        try:
            with os.scandir(abs_dir) as entries:
                for entry in entries:
                    if entry.is_file() and not entry.name.startswith('.'):
                        rel_path = os.path.join(rel_dir, entry.name) 
                        contents.append(rel_path)
        except NotADirectoryError:
            # If it's a file, just return the file
            contents = [rel_dir]
            
        if contents:
            coder.io.tool_output(f"📋 Listed {len(contents)} file(s) in '{dir_path}'")
            if len(contents) > 10:
                return f"Found {len(contents)} files: {', '.join(contents[:10])}..."
            else:
                return f"Found {len(contents)} files: {', '.join(contents)}"
        else:
            coder.io.tool_output(f"📋 No files found in '{dir_path}'")
            return f"No files found in directory"
    except Exception as e:
        coder.io.tool_error(f"Error in ls: {str(e)}")
        return f"Error: {str(e)}"
