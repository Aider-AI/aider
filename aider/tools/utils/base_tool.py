from abc import ABC, abstractmethod

from aider.tools.utils.helpers import handle_tool_error


class BaseTool(ABC):
    """Abstract base class for all tools."""

    # Class properties that must be defined by subclasses
    NORM_NAME = None
    SCHEMA = None

    @abstractmethod
    def execute(self, coder, **params):
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
        instance = cls()
        try:
            return instance.execute(coder, **params)
        except Exception as e:
            return handle_tool_error(coder, cls.__name__, e)

    @staticmethod
    def format_output(result):
        """
        Format the output for display.

        Args:
            result: The result from execute()

        Returns:
            str: Formatted output
        """
        return str(result)
