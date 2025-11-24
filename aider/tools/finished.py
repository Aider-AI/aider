from aider.tools.utils.base_tool import BaseTool


class Tool(BaseTool):
    NORM_NAME = "finished"
    SCHEMA = {
        "type": "function",
        "function": {
            "name": "Finished",
            "description": (
                "Declare that we are done with every single sub goal and no further work is needed."
            ),
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
        Mark that the current generation task needs no further effort.

        This gives the LLM explicit control over when it can stop looping
        """

        if coder:
            coder.agent_finished = True
            # coder.io.tool_output("Task Finished!")
            return "Task Finished!"

        # coder.io.tool_Error("Error: Could not mark agent task as finished")
        return "Error: Could not mark agent task as finished"
