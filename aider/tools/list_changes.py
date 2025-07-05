import traceback
from datetime import datetime

def _execute_list_changes(coder, file_path=None, limit=10):
    """
    List recent changes made to files.
    
    Parameters:
    - coder: The Coder instance
    - file_path: Optional path to filter changes by file
    - limit: Maximum number of changes to list
    
    Returns a formatted list of changes.
    """
    try:
        # If file_path is specified, get the absolute path
        rel_file_path = None
        if file_path:
            abs_path = coder.abs_root_path(file_path)
            rel_file_path = coder.get_rel_fname(abs_path)
        
        # Get the list of changes
        changes = coder.change_tracker.list_changes(rel_file_path, limit)
        
        if not changes:
            if file_path:
                return f"No changes found for file '{file_path}'"
            else:
                return "No changes have been made yet"
        
        # Format the changes into a readable list
        result = "Recent changes:\n"
        for i, change in enumerate(changes):
            change_time = datetime.fromtimestamp(change['timestamp']).strftime('%H:%M:%S')
            change_type = change['type']
            file_path = change['file_path']
            change_id = change['id']
            
            result += f"{i+1}. [{change_id}] {change_time} - {change_type.upper()} on {file_path}\n"
         
        coder.io.tool_output(result) # Also print to console for user
        return result
             
    except Exception as e:
        coder.io.tool_error(f"Error in ListChanges: {str(e)}\n{traceback.format_exc()}") # Add traceback
        return f"Error: {str(e)}"
