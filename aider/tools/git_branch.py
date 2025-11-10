from aider.repo import ANY_GIT_ERROR

schema = {
    "type": "function",
    "function": {
        "name": "GitBranch",
        "description": "List branches in the repository.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "gitbranch"


def _execute_git_branch(coder):
    """
    List branches in the repository.
    """
    if not coder.repo:
        return "Not in a git repository."

    try:
        # Get all branches and current branch
        branches = []
        current_branch = coder.repo.repo.active_branch.name
        for branch in coder.repo.repo.heads:
            prefix = "* " if branch.name == current_branch else "  "
            branches.append(f"{prefix}{branch.name}")
        return "\n".join(branches)
    except ANY_GIT_ERROR as e:
        coder.io.tool_error(f"Error running git branch: {e}")
        return f"Error running git branch: {e}"


def process_response(coder, params):
    """
    Process the GitBranch tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters (should be empty for GitBranch)

    Returns:
        str: Result message
    """
    # GitBranch tool has no parameters to validate
    return _execute_git_branch(coder)
