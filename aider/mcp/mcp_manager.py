from contextlib import AsyncExitStack
from dataclasses import dataclass
import re
import shlex
import threading
import queue
from typing import Dict, List, Optional
import asyncio

from mcp import ClientSession, StdioServerParameters, stdio_client

from aider.mcp.mcp_server import McpServer
from aider.mcp.mcp_tool import McpTool

@dataclass
class CallArguments:
    server_name: str
    function: str
    args: dict

@dataclass
class CallResponse:
    error: str | None
    response: str | None

class McpManager:
    """Manages MCP servers and tools configuration."""

    def __init__(self):
        self.servers: Dict[str, McpServer] = {}
        self.enabled: bool = False
        self.message_queue = queue.Queue()
        self.result_queue = queue.Queue()

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get the current event loop or create a new one if none exists."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return asyncio.new_event_loop()

    def _call(self, io, server_name, function, args: dict = {}):
        """Sync call to the thread with queues."""

        self.message_queue.put(CallArguments(server_name, function, args))
        result = self.result_queue.get()
        self.result_queue.task_done()

        if result.error:
            if io:
                io.tool_error(result.error)
            return None

        return result.response

    async def _async_server_loop(self, server: McpServer) -> None:
        """Run the async server loop for a given server."""

        # Parse the server exec command
        command_parts = shlex.split(server.command)
        executable = command_parts[0]
        args = command_parts[1:]

        server_params = StdioServerParameters(
            command=executable,
            args=args,
            env=server.env_vars,
        )

        # Run the async server loop
        exit_stack = AsyncExitStack()

        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()

        while True:
            msg: CallArguments = self.message_queue.get()

            # Exit the loop if the exit message is received
            if msg.function == "exit":
                break

            # Ignore messages for other servers
            if msg.server_name != server.name:
                self.message_queue.task_done()
                continue

            try:
                if msg.function == "call_tool":
                    response = await session.call_tool(**msg.args)
                    self.result_queue.put(CallResponse(None, response))
                elif msg.function == "list_tools":
                    response = await session.list_tools()
                    self.result_queue.put(CallResponse(None, response))
            except Exception as e:
                self.result_queue.put(CallResponse(str(e), None))
            finally:
                self.message_queue.task_done()

    def _server_loop(self, server: McpServer, loop: asyncio.AbstractEventLoop) -> None:
        """Wrap the async server loop for a given server."""
        loop.run_until_complete(self._async_server_loop(server))

    def configure_from_args(self, args) -> None:
        """Configure MCP from command-line arguments."""
        self.enabled = args.mcp

        # If MCP is not enabled, don't process further
        if not self.enabled:
            return

        # Add servers specified in --mcp-servers
        for server_name in args.mcp_servers:
            self.add_server(server_name)
            self.servers[server_name].enabled = True

        # Process server commands
        for cmd_spec in args.mcp_server_command:
            parts = cmd_spec.split(":", 1)
            if len(parts) != 2:
                continue
            server_name, command = parts
            self.add_server(server_name)
            self.servers[server_name].command = command

        # Process server environment variables
        for env_spec in args.mcp_server_env:
            match = re.match(r"([^:]+):([^=]+)=(.*)", env_spec)
            if not match:
                continue
            server_name, env_var, value = match.groups()
            self.add_server(server_name)
            self.servers[server_name].env_vars[env_var] = value

        # Process tool permissions
        for perm_spec in args.mcp_tool_permission:
            match = re.match(r"([^:]+):([^=]+)=(.*)", perm_spec)
            if not match:
                continue
            server_name, tool_name, permission = match.groups()
            if permission not in ["manual", "auto"]:
                continue
            self.add_server(server_name)
            if tool_name not in self.servers[server_name].tools:
                self.servers[server_name].add_tool(tool_name)
            self.servers[server_name].set_tool_permission(tool_name, permission)

    def add_server(self, server_name: str) -> McpServer:
        """Add a new server if it doesn't exist, or return the existing one."""
        if server_name not in self.servers:
            self.servers[server_name] = McpServer(server_name)
        return self.servers[server_name]

    def get_server(self, server_name: str) -> Optional[McpServer]:
        """Get a server by name, or None if it doesn't exist."""
        return self.servers.get(server_name)

    def get_enabled_servers(self) -> List[McpServer]:
        """Get a list of all enabled servers."""
        return [server for server in self.servers.values() if server.enabled]

    def list_servers(self) -> List[McpServer]:
        """Get a list of all servers."""
        return list(self.servers.values())

    def list_tools(self) -> Dict[str, List[McpTool]]:
        """Get a dictionary of server names to lists of tools."""
        result = {}
        for server_name, server in self.servers.items():
            if server.tools:
                result[server_name] = list(server.tools.values())
        return result

    def initialize_servers(self, io) -> None:
        """Initialize and start all enabled MCP servers.

        Args:
            io: InputOutput object for logging messages
        """
        if not self.enabled:
            return

        loop = self._get_event_loop()

        for server in self.get_enabled_servers():
            if server.command:
                t = threading.Thread(target=self._server_loop, args=(server, loop))
                t.start()
            else:
                io.tool_warning(f"MCP server '{server.name}' has no command configured")


    def discover_tools(self, io) -> None:
        """Discover tools from all enabled servers.

        Args:
            io: InputOutput object for logging messages
        """
        if not self.enabled:
            return

        for server in self.get_enabled_servers():
            # Check if the server configuration is valid
            if not server.is_valid():
                if io:
                    io.tool_warning(f"Cannot discover tools for server '{server.name}': Invalid configuration (must have a command)")
                continue

            response = self._call(io, server.name, "list_tools", {})

            # Process the tools
            for tool in response.tools:
                name = tool.name
                description = tool.description
                input_schema = tool.inputSchema

                # Get the permission from the existing tool configuration or default to "manual"
                permission = "manual"
                if name in server.tools:
                    permission = server.tools[name].permission

                # Add the tool to the server configuration
                server.add_tool(name, permission, description, input_schema)

    def execute_tool(self, server_name: str, tool_name: str, arguments: dict, io) -> str:
        """Execute an MCP tool with the given arguments.

        Args:
            server_name: The name of the server providing the tool
            tool_name: The name of the tool to execute
            arguments: A dictionary of arguments to pass to the tool
            io: InputOutput object for logging messages

        Returns:
            The result of the tool execution as a string
        """
        if not self.enabled:
            io.tool_error("MCP is not enabled")
            return "MCP is not enabled"

        server = self.get_server(server_name)
        if not server:
            io.tool_error(f"MCP server '{server_name}' not found")
            return f"MCP server '{server_name}' not found"

        if not server.enabled:
            io.tool_error(f"MCP server '{server_name}' is not enabled")
            return f"MCP server '{server_name}' is not enabled"

        if tool_name not in server.tools:
            io.tool_error(f"Tool '{tool_name}' not found in server '{server_name}'")
            return f"Tool '{tool_name}' not found in server '{server_name}'"

        # Get the tool permission
        tool = server.tools[tool_name]
        permission = tool.permission

        # Check if the tool requires manual approval
        if permission == "manual":
            if not io.confirm_ask(f"Allow execution of tool '{tool_name}' from server '{server_name}'?"):
                return "Tool execution denied by user"

        # Execute the tool
        try:
            response = self._call(io, server_name, "call_tool", {
                "name": tool_name,
                "arguments": arguments
            })

            # Process the response
            result = ""
            for content_item in response.content:
                if content_item.type == "text":
                    result += content_item.text

            io.tool_output(f"Tool '{tool_name}' executed successfully")

            return result
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            io.tool_error(error_msg)
            return error_msg

    def stop_servers(self) -> None:
        """Stop all running MCP servers."""
        self.message_queue.put(CallArguments("", "exit", {}))