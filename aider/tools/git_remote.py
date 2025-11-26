from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitremote"
    SCHEMA = {
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

    @classmethod
    def execute(cls, coder):
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
