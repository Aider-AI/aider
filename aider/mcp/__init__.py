#!/usr/bin/env python

from typing import Dict, List, Tuple

from aider.mcp.mcp_manager import McpManager
from aider.mcp.mcp_server import McpServer
from aider.mcp.mcp_tool import McpTool
from aider.mcp.mcp_tool_parser import McpToolParser

# Global instance of the MCP manager
mcp_manager = McpManager()

def configure_mcp(args) -> None:
    """Configure the MCP manager from command-line arguments."""
    mcp_manager.configure_from_args(args)

def stop_mcp_servers() -> None:
    """Quit all enabled MCP servers."""
    mcp_manager.stop_servers()

def is_mcp_enabled() -> bool:
    """Check if MCP is enabled."""
    return mcp_manager.enabled

def list_mcp_servers() -> List[McpServer]:
    """List all configured MCP servers."""
    return mcp_manager.list_servers()

def list_mcp_tools() -> Dict[str, List[McpTool]]:
    """List all available MCP tools grouped by server."""
    return mcp_manager.list_tools()

def initialize_mcp_servers(io) -> None:
    """Initialize and start all enabled MCP servers.

    Args:
        io: InputOutput object for logging messages
    """
    mcp_manager.initialize_servers(io)

def _execute_mcp_tool(server_name: str, tool_name: str, arguments: dict, io) -> str:
    """Execute an MCP tool with the given arguments.

    Args:
        server_name: The name of the server providing the tool
        tool_name: The name of the tool to execute
        arguments: A dictionary of arguments to pass to the tool
        io: InputOutput object for logging messages

    Returns:
        The result of the tool execution as a string
    """
    return mcp_manager.execute_tool(server_name, tool_name, arguments, io)

def execute_mcp_tool(server_name: str, tool_name: str, arguments: dict, io) -> str:
    """Execute an MCP tool with the given arguments.

    Args:
        server_name: The name of the server providing the tool
        tool_name: The name of the tool to execute
        arguments: A dictionary of arguments to pass to the tool
        io: InputOutput object for logging messages

    Returns:
        The result of the tool execution as a string
    """
    return _execute_mcp_tool(server_name, tool_name, arguments, io)

def process_llm_tool_requests(text: str, io) -> list[str]:
    """
    Process tools execution request from the LLM.

    Args:
        text: The text to parse for tool execution requests
        io: InputOutput object for logging messages

    Returns:
        A list of results from processed tool requests
    """
    tool_requests = McpToolParser.extract_tool_requests(text)

    results = []
    for (server_name, tool_name, arguments) in tool_requests:
        result, _ = process_llm_tool_request(server_name, tool_name, arguments, io)
        results.append(result)

    return results

def process_llm_tool_request(server_name: str, tool_name: str, arguments: dict, io) -> Tuple[str, bool]:
    """
    Process a single tool execution request from the LLM.

    Args:
        server_name: The name of the server providing the tool
        tool_name: The name of the tool to execute
        arguments: A dictionary of arguments to pass to the tool
        io: InputOutput object for logging messages

    Returns:
        A tuple containing the result of the tool execution as a string and a boolean indicating if an error
        occurred during the execution
    """
    # Check if the server and tool exist
    server = mcp_manager.get_server(server_name)
    identifier = f"{server_name}.{tool_name}"
    if not server:
        error = f"MCP server '{server_name}' not found"
        io.tool_error(error)
        return McpToolParser.format_tool_error(identifier, error), True

    if tool_name not in server.tools:
        error = f"Tool '{tool_name}' not found in server '{server_name}'"
        io.tool_error(error)
        return McpToolParser.format_tool_error(identifier, error), True

    try:
        result = _execute_mcp_tool(server_name, tool_name, arguments, io)
        return McpToolParser.format_tool_result(identifier, result), False
    except Exception as e:
        error = f"Error executing tool '{tool_name}': {str(e)}"
        io.tool_error(error)
        return McpToolParser.format_tool_error(identifier, error), True

def get_available_tools_prompt() -> str:
    """
    Get a formatted string describing the available MCP tools for inclusion in the system prompt.

    Returns:
        A formatted string describing the available tools
    """
    tools_by_server = list_mcp_tools()
    return McpToolParser.format_available_tools(tools_by_server)
