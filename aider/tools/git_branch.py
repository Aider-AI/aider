from aider.repo import ANY_GIT_ERROR
from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "gitbranch"
    SCHEMA = {
        "type": "function",
        "function": {
            "name": "GitBranch",
            "description": (
                "List branches in the repository with various filtering and formatting options."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "remotes": {
                        "type": "boolean",
                        "description": "List remote-tracking branches (-r/--remotes flag)",
                    },
                    "all": {
                        "type": "boolean",
                        "description": "List both local and remote branches (-a/--all flag)",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": (
                            "Show verbose information including commit hash and subject (-v flag)"
                        ),
                    },
                    "very_verbose": {
                        "type": "boolean",
                        "description": (
                            "Show very verbose information including upstream branch (-vv flag)"
                        ),
                    },
                    "merged": {
                        "type": "string",
                        "description": "Show branches merged into specified commit (--merged flag)",
                    },
                    "no_merged": {
                        "type": "string",
                        "description": (
                            "Show branches not merged into specified commit (--no-merged flag)"
                        ),
                    },
                    "sort": {
                        "type": "string",
                        "description": (
                            "Sort branches by key (committerdate, authordate, refname, etc.)"
                            " (--sort flag)"
                        ),
                    },
                    "format": {
                        "type": "string",
                        "description": "Custom output format using placeholders (--format flag)",
                    },
                    "show_current": {
                        "type": "boolean",
                        "description": "Show only current branch name (--show-current flag)",
                    },
                },
                "required": [],
            },
        },
    }

    @classmethod
    def execute(
        cls,
        coder,
        remotes=False,
        all=False,
        verbose=False,
        very_verbose=False,
        merged=None,
        no_merged=None,
        sort=None,
        format=None,
        show_current=False,
    ):
        """
        List branches in the repository with various filtering and formatting options.
        """
        if not coder.repo:
            return "Not in a git repository."

        try:
            # Build git command arguments
            args = []

            # Handle boolean flags
            if remotes:
                args.append("--remotes")
            if all:
                args.append("--all")
            if verbose:
                args.append("--verbose")
            if very_verbose:
                args.append("--verbose")
                args.append("--verbose")
            if show_current:
                args.append("--show-current")

            # Handle string parameters
            if merged:
                args.extend(["--merged", merged])
            if no_merged:
                args.extend(["--no-merged", no_merged])
            if sort:
                args.extend(["--sort", sort])
            if format:
                args.extend(["--format", format])

            # Execute git command
            result = coder.repo.repo.git.branch(*args)

            # If no result and show_current was used, get current branch directly
            if not result and show_current:
                current_branch = coder.repo.repo.active_branch.name
                return current_branch

            return result if result else "No branches found matching the criteria."

        except ANY_GIT_ERROR as e:
            coder.io.tool_error(f"Error running git branch: {e}")
            return f"Error running git branch: {e}"
