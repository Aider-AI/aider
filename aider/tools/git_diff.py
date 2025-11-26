from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitdiff"
    SCHEMA = {
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
                        "description": (
                            "The branch or commit hash to diff against. Defaults to HEAD."
                        ),
                    },
                },
                "required": [],
            },
        },
    }

    @classmethod
    def execute(cls, coder, branch=None):
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
