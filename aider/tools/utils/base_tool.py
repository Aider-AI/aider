from abc import ABC, abstractmethod

from aider.tools.utils.helpers import handle_tool_error
from aider.tools.utils.output import print_tool_response


class BaseTool(ABC):
    """Abstract base class for all tools."""

    # Class properties that must be defined by subclasses
    # Note: NORM_NAME should be the lowercase version of the function name in the SCHEMA
    NORM_NAME = None
    SCHEMA = None

    @classmethod
    @abstractmethod
    def execute(cls, coder, **params):
        """
        Execute the tool with the given parameters.

        Args:
            coder: The Coder instance
            **params: Tool-specific parameters

        Returns:
            str: Result message
        """
        pass

    @classmethod
    def process_response(cls, coder, params):
        """
        Process the tool response by creating an instance and calling execute.

        Args:
            coder: The Coder instance
            params: Dictionary of parameters

        Returns:
            str: Result message
        """

        # Validate required parameters from SCHEMA
        if cls.SCHEMA and "function" in cls.SCHEMA:
            function_schema = cls.SCHEMA["function"]

            if "parameters" in function_schema and "required" in function_schema["parameters"]:
                required_params = function_schema["parameters"]["required"]
                missing_params = [param for param in required_params if param not in params]
                if missing_params:
                    tool_name = function_schema.get("name", "Unknown Tool")
                    error_msg = (
                        f"Missing required parameters for {tool_name}: {', '.join(missing_params)}"
                    )
                    return handle_tool_error(coder, tool_name, ValueError(error_msg))

        try:
            return cls.execute(coder, **params)
        except Exception as e:
            return handle_tool_error(coder, cls.SCHEMA.get("function").get("name"), e)

    @classmethod
    def format_output(cls, coder, mcp_server, tool_response):
        print_tool_response(coder=coder, mcp_server=mcp_server, tool_response=tool_response)
