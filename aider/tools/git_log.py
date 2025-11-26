from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitlog"
    SCHEMA = {
        "type": "function",
        "function": {
            "name": "GitLog",
            "description": "Show the git log.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of commits to show. Defaults to 10.",
                    },
                },
                "required": [],
            },
        },
    }

    @classmethod
    def execute(cls, coder, limit=10):
        """
        Show the git log.
        """
        if not coder.repo:
            return "Not in a git repository."

        try:
            commits = list(coder.repo.repo.iter_commits(max_count=limit))
            log_output = []
            for commit in commits:
                short_hash = commit.hexsha[:8]
                message = commit.message.strip().split("\n")[0]
                log_output.append(f"{short_hash} {message}")
            return "\n".join(log_output)
        except ANY_GIT_ERROR as e:
            coder.io.tool_error(f"Error running git log: {e}")
            return f"Error running git log: {e}"
