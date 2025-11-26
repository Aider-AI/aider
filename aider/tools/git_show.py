from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitshow"
    SCHEMA = {
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

    @classmethod
    def execute(cls, coder, object="HEAD"):
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
