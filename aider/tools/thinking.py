import json

from aider.tools.utils.base_tool import BaseTool
from aider.tools.utils.output import color_markers, tool_footer, tool_header


class Tool(BaseTool):
    NORM_NAME = "thinking"
    SCHEMA = {
        "type": "function",
        "function": {
            "name": "Thinking",
            "description": (
                "Use this tool to store useful facts for later "
                "keep a scratch pad of your current efforts "
                "and clarify your thoughts and intentions for your next steps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Textual information to record in the context",
                    },
                },
                "required": ["content"],
            },
        },
    }

    @classmethod
    def execute(cls, coder, content):
        """
        A place to allow the model to record freeform text as it
        iterates over tools to ideally help it guide itself to a proper solution
        """
        coder.io.tool_output("🧠 Thoughts recorded in context")
        return content

    @classmethod
    def format_output(cls, coder, mcp_server, tool_response):
        color_start, color_end = color_markers(coder)
        params = json.loads(tool_response.function.arguments)

        tool_header(coder=coder, mcp_server=mcp_server, tool_response=tool_response)

        coder.io.tool_output("")
        coder.io.tool_output(f"{color_start}Thoughts:{color_end}")
        coder.io.tool_output(params["content"])
        coder.io.tool_output("")

        tool_footer(coder=coder, tool_response=tool_response)
