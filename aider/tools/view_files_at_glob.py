import os
import fnmatch

def execute_view_files_at_glob(coder, pattern):
    """
    Execute a glob pattern and add matching files to context as read-only.

    This tool helps the LLM find files by pattern matching, similar to
    how a developer would use glob patterns to find files.
    """
    try:
        # Find files matching the pattern
        matching_files = []
        
        # Make the pattern relative to root if it's absolute
        if pattern.startswith('/'):
            pattern = os.path.relpath(pattern, coder.root)
        
        # Get all files in the repo
        all_files = coder.get_all_relative_files()
        
        # Find matches with pattern matching
        for file in all_files:
            if fnmatch.fnmatch(file, pattern):
                matching_files.append(file)
        
        # Limit the number of files added if there are too many matches
        if len(matching_files) > coder.max_files_per_glob:
            coder.io.tool_output(
                f"⚠️ Found {len(matching_files)} files matching '{pattern}', "
                f"limiting to {coder.max_files_per_glob} most relevant files."
            )
            # Sort by modification time (most recent first)
            matching_files.sort(key=lambda f: os.path.getmtime(coder.abs_root_path(f)), reverse=True)
            matching_files = matching_files[:coder.max_files_per_glob]
            
        # Add files to context
        for file in matching_files:
            # Use the coder's internal method to add files
            coder._add_file_to_context(file)
        
        # Return a user-friendly result
        if matching_files:
            if len(matching_files) > 10:
                brief = ', '.join(matching_files[:5]) + f', and {len(matching_files)-5} more'
                coder.io.tool_output(f"📂 Added {len(matching_files)} files matching '{pattern}': {brief}")
            else:
                coder.io.tool_output(f"📂 Added files matching '{pattern}': {', '.join(matching_files)}")
            return f"Added {len(matching_files)} files: {', '.join(matching_files[:5])}{' and more' if len(matching_files) > 5 else ''}"
        else:
            coder.io.tool_output(f"⚠️ No files found matching '{pattern}'")
            return f"No files found matching '{pattern}'"
    except Exception as e:
        coder.io.tool_error(f"Error in ViewFilesAtGlob: {str(e)}")
        return f"Error: {str(e)}"
