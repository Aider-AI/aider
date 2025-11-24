from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitstatus"
    SCHEMA = {
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

    @classmethod
    def execute(cls, coder):
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
