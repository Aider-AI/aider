schema = {
    "type": "function",
    "function": {
        "name": "MakeReadonly",
        "description": "Make an editable file read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to make read-only.",
                },
            },
            "required": ["file_path"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "makereadonly"


def _execute_make_readonly(coder, file_path):
    """
    Convert an editable file to a read-only file.

    This allows the LLM to downgrade a file from editable to read-only
    when it determines it no longer needs to make changes to that file.
    """
    try:
        # Get absolute path
        abs_path = coder.abs_root_path(file_path)

        # Check if file is in editable context
        if abs_path not in coder.abs_fnames:
            if abs_path in coder.abs_read_only_fnames:
                coder.io.tool_output(f"📚 File '{file_path}' is already read-only")
                return "File is already read-only"
            else:
                coder.io.tool_output(f"⚠️ File '{file_path}' not in context")
                return "File not in context"

        # Move from editable to read-only
        coder.abs_fnames.remove(abs_path)
        coder.abs_read_only_fnames.add(abs_path)

        coder.io.tool_output(f"📚 Made '{file_path}' read-only")
        return "File is now read-only"
    except Exception as e:
        coder.io.tool_error(f"Error making file read-only: {str(e)}")
        return f"Error: {str(e)}"


def process_response(coder, params):
    """
    Process the MakeReadonly tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    file_path = params.get("file_path")
    if file_path is not None:
        return _execute_make_readonly(coder, file_path)
    else:
        return "Error: Missing 'file_path' parameter for MakeReadonly"
