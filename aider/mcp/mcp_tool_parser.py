#!/usr/bin/env python

import json
import re
from typing import Dict, Optional, Tuple, Any


class McpToolParser:
    """Parser for MCP tool execution requests from LLM output."""

    # Regular expression pattern for extracting tool execution requests
    TOOL_PATTERN = re.compile(
        r'<use_mcp_tool>\s*'
        r'<server_name>(.*?)</server_name>\s*'
        r'<tool_name>(.*?)</tool_name>\s*'
        r'<arguments>\s*([\s\S]*?)\s*</arguments>\s*'
        r'</use_mcp_tool>',
        re.DOTALL
    )

    @classmethod
    def extract_tool_requests(cls, text: str) -> list[Tuple[str, str, Dict[str, Any]]]:
        """
        Extract MCP tools execution request from text.

        Args:
            text: The text to parse for tool execution requests

        Returns:
            A list of (server_name, tool_name, arguments) if a request is found,
        """
        match = cls.TOOL_PATTERN.findall(text)

        return [
            (
                server_name.strip(),
                tool_name.strip(),
                McpToolParser.parse_arguments(arguments)
            )
            for server_name, tool_name, arguments in match
        ]

    @classmethod
    def parse_arguments(cls, arguments_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse the arguments string into a dictionary.

        Args:
            arguments_str: The arguments string to parse
        """

        try:
            return json.loads(arguments_str.strip())
        except json.JSONDecodeError:
            # If JSON parsing fails, return None
            return None

    @classmethod
    def format_tool_result(cls, identifier: str, result: str) -> str:
        """
        Format the result of a tool execution for the LLM.

        Args:
            identifier: The identifier for the tool execution
            result: The result of the tool execution

        Returns:
            The formatted result
        """
        return f"""
Tool execution result for {identifier}:
```
{result}
```
"""

    @classmethod
    def format_tool_error(cls, identifier: str, error: str) -> str:
        """
        Format an error message for the LLM.

        Args:
            identifier: The identifier for the tool execution
            error: The error message

        Returns:
            The formatted error message
        """
        return f"""
Tool execution error for {identifier}:
```
{error}
```
"""

    @classmethod
    def format_available_tools(cls, tools_by_server: Dict[str, list]) -> str:
        """
        Format the available tools for inclusion in the system prompt.

        Args:
            tools_by_server: A dictionary mapping server names to lists of tools

        Returns:
            A formatted string describing the available tools
        """
        if not tools_by_server:
            return "No MCP tools available."

        result = "# Available MCP Tools\n\n"
        result += "You can use the following MCP tools by including a tool execution request in your response:\n\n"

        for server_name, tools in tools_by_server.items():
            result += f"## Server: {server_name}\n\n"

            for tool in tools:
                result += f"### {tool.name}\n\n"

                if tool.description:
                    result += f"{tool.description}\n\n"

                result += "**Permission:** " + tool.permission + "\n\n"

                if tool.input_schema:
                    result += "**Input Schema:**\n```json\n"
                    result += json.dumps(tool.input_schema, indent=2)
                    result += "\n```\n\n"

                result += "**Usage Example:**\n```\n"
                result += "<use_mcp_tool>\n"
                result += f"<server_name>{server_name}</server_name>\n"
                result += f"<tool_name>{tool.name}</tool_name>\n"
                result += "<arguments>\n"

                # Generate example arguments based on the input schema
                if tool.input_schema and "properties" in tool.input_schema:
                    example_args = {}
                    for prop_name, prop_info in tool.input_schema["properties"].items():
                        if prop_info.get("type") == "string":
                            example_args[prop_name] = f"example_{prop_name}"
                        elif prop_info.get("type") == "number":
                            example_args[prop_name] = 42
                        elif prop_info.get("type") == "boolean":
                            example_args[prop_name] = True
                        elif prop_info.get("type") == "array":
                            example_args[prop_name] = []
                        elif prop_info.get("type") == "object":
                            example_args[prop_name] = {}
                        else:
                            example_args[prop_name] = "value"

                    result += json.dumps(example_args, indent=2)
                else:
                    result += "{\n  \"param1\": \"value1\",\n  \"param2\": \"value2\"\n}"

                result += "\n</arguments>\n"
                result += "</use_mcp_tool>\n```\n\n"

        return result
