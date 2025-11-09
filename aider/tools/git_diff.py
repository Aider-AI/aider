from aider.repo import ANY_GIT_ERROR

schema = {
    "type": "function",
    "function": {
        "name": "GitDiff",
        "description": (
            "Show the diff between the current working directory and a git branch or commit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "The branch or commit hash to diff against. Defaults to HEAD.",
                },
            },
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "gitdiff"


def _execute_git_diff(coder, branch=None):
    """
    Show the diff between the current working directory and a git branch or commit.
    """
    if not coder.repo:
        return "Not in a git repository."

    try:
        if branch:
            diff = coder.repo.diff_commits(False, branch, "HEAD")
        else:
            diff = coder.repo.diff_commits(False, "HEAD", None)

        if not diff:
            return "No differences found."
        return diff
    except ANY_GIT_ERROR as e:
        coder.io.tool_error(f"Error running git diff: {e}")
        return f"Error running git diff: {e}"


def process_response(coder, params):
    """
    Process the GitDiff tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    branch = params.get("branch")
    return _execute_git_diff(coder, branch)
