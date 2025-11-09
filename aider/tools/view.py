schema = {
    "type": "function",
    "function": {
        "name": "View",
        "description": (
            "View a specific file and add it to context."
            "Only use this when the file is not already in the context "
            "and when editing the file is necessary to accomplish the goal."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to view.",
                },
            },
            "required": ["file_path"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "view"


def execute_view(coder, file_path):
    """
    Explicitly add a file to context as read-only.

    This gives the LLM explicit control over what files to view,
    rather than relying on indirect mentions.
    """
    try:
        # Use the coder's helper, marking it as an explicit view request
        return coder._add_file_to_context(file_path, explicit=True)
    except Exception as e:
        coder.io.tool_error(f"Error viewing file: {str(e)}")
        return f"Error: {str(e)}"


def process_response(coder, params):
    """
    Process the View tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    file_path = params.get("file_path")
    if file_path is not None:
        return execute_view(coder, file_path)
    else:
        return "Error: Missing 'file_path' parameter for View"
