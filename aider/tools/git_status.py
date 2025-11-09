from aider.repo import ANY_GIT_ERROR

schema = {
    "type": "function",
    "function": {
        "name": "GitStatus",
        "description": "Show the working tree status.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "gitstatus"


def _execute_git_status(coder):
    """
    Show the working tree status.
    """
    if not coder.repo:
        return "Not in a git repository."

    try:
        return coder.repo.repo.git.status()
    except ANY_GIT_ERROR as e:
        coder.io.tool_error(f"Error running git status: {e}")
        return f"Error running git status: {e}"


def process_response(coder, params):
    """
    Process the GitStatus tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters (should be empty for GitStatus)

    Returns:
        str: Result message
    """
    # GitStatus tool has no parameters to validate
    return _execute_git_status(coder)
