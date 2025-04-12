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
