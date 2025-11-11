from aider.repo import ANY_GIT_ERROR

schema = {
    "type": "function",
    "function": {
        "name": "GitRemote",
        "description": "List remote repositories.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "gitremote"


def _execute_git_remote(coder):
    """
    List remote repositories.
    """
    if not coder.repo:
        return "Not in a git repository."

    try:
        remotes = coder.repo.repo.remotes
        if not remotes:
            return "No remotes configured."

        result = []
        for remote in remotes:
            result.append(f"{remote.name}\t{remote.url}")
        return "\n".join(result)
    except ANY_GIT_ERROR as e:
        coder.io.tool_error(f"Error running git remote: {e}")
        return f"Error running git remote: {e}"


def process_response(coder, params):
    """
    Process the GitRemote tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters (should be empty for GitRemote)

    Returns:
        str: Result message
    """
    # GitRemote tool has no parameters to validate
    return _execute_git_remote(coder)
