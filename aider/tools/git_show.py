from aider.repo import ANY_GIT_ERROR

schema = {
    "type": "function",
    "function": {
        "name": "GitShow",
        "description": "Show various types of objects (blobs, trees, tags, and commits).",
        "parameters": {
            "type": "object",
            "properties": {
                "object": {
                    "type": "string",
                    "description": "The object to show. Defaults to HEAD.",
                },
            },
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "gitshow"


def _execute_git_show(coder, object="HEAD"):
    """
    Show various types of objects (blobs, trees, tags, and commits).
    """
    if not coder.repo:
        return "Not in a git repository."

    try:
        return coder.repo.repo.git.show(object)
    except ANY_GIT_ERROR as e:
        coder.io.tool_error(f"Error running git show: {e}")
        return f"Error running git show: {e}"


def process_response(coder, params):
    """
    Process the GitShow tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    object = params.get("object", "HEAD")
    return _execute_git_show(coder, object)
