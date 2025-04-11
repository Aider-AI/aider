from contextlib import AsyncExitStack
from dataclasses import dataclass
import os
import shlex
import threading
import queue
import time
from typing import Dict, List, Optional
import asyncio

from mcp import ClientSession, StdioServerParameters, stdio_client
import yaml

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
        self.mcp_thread = threading.Thread(target=self._servers_loop, args=(self.servers.values(),),)

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get the current event loop or create a new one if none exists."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return asyncio.new_event_loop()

    def _call(self, io, server_name, function, args: dict = {}):
        """Sync call to the thread with queues."""

        self.message_queue.put_nowait(CallArguments(server_name, function, args))

        while True:
            try:
                print("Waiting for result")
                result = self.result_queue.get_nowait()
                print("Got result", result)

                if result.error:
                    if io:
                        io.tool_error(result.error)
                    return None

                return result.response
            except KeyboardInterrupt:
                if io:
                    io.tool_error("Keyboard interrupt in MCP call")
                return CallResponse("Keyboard interrupt", None)
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                if io:
                    io.tool_error(f"Error in MCP call: {str(e)}")
                return CallResponse(str(e), None)

    async def _start_server_session(self, server: McpServer, exit_stack: AsyncExitStack) -> ClientSession:
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

        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()
        return session

    async def _async_servers_loop(self, servers: list[McpServer]) -> None:
        """Run the async server loop for all servers in parallel."""
        exit_stack = AsyncExitStack()

        sessions = { server.name: (server, await self._start_server_session(server, exit_stack)) for server in servers }

        try:
            while True:
                try:
                    msg: CallArguments = self.message_queue.get_nowait()
                    print("Got message", msg)

                    # Exit the loop if the exit message is received
                    if msg.function == "exit":
                        print("Exit message received")
                        break

                    # Find the server and session for the given server name
                    server, session = sessions.get(msg.server_name, (None, None))
                    if not server:
                        print(f"Server '{msg.server_name}' not found")
                        continue

                    try:
                        if msg.function == "call_tool":
                            response = await session.call_tool(**msg.args)
                            print("Put response in queue 1")
                            self.result_queue.put_nowait(CallResponse(None, response))
                        elif msg.function == "list_tools":
                            response = await session.list_tools()
                            print("Put response in queue 2")
                            self.result_queue.put_nowait(CallResponse(None, response))
                    except Exception as e:
                        print("Put response in queue 3")
                        self.result_queue.put_nowait(CallResponse(str(e), None))
                except queue.Empty:
                    await asyncio.sleep(0.1)
        except:
            print("Error in async server loop")

    def _servers_loop(self, servers: list[McpServer]) -> None:
        """Wrap the async server loop for a given server."""
        try:
            loop = self._get_event_loop()
            loop.run_until_complete(self._async_servers_loop(servers))
        except Exception as e:
            print(f"Error in servers loop: {str(e)}")
        finally:
            loop.close()

    def configure_from_args(self, args) -> None:
        """Configure MCP from command-line arguments."""
        self.enabled = args.mcp_configuration is not None

        # If MCP is not enabled, don't process further
        if not self.enabled:
            return

        # Read file from the running directory
        expanded_path = os.path.expanduser(args.mcp_configuration)
        absolute_mcp_config_path = os.path.abspath(expanded_path)

        # Check if the file exists
        if not os.path.exists(absolute_mcp_config_path):
            raise FileNotFoundError(f"MCP configuration file '{absolute_mcp_config_path}' not found")

        with open(absolute_mcp_config_path) as f:
            mcp_configuration = yaml.safe_load(f)

            # Add servers specified in mcp.servers
            for server_info in mcp_configuration.get("servers", []):
                server = McpServer(
                    name=server_info.get("name"),
                    command=server_info.get("command"),
                    env_vars=server_info.get("envs", {}),
                )

                for name, perm in server_info.get("permissions", []).items():
                    if perm not in ["manual", "auto"]:
                        continue

                    server.set_tool(tool_name=name, permission=perm)

                self.servers[server_info.get("name")] = server

    def get_server(self, server_name: str) -> Optional[McpServer]:
        """Get a server by name, or None if it doesn't exist."""
        return self.servers.get(server_name)

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

        self.mcp_thread.start()

        for server in self.servers.values():
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
                server.set_tool(
                    tool_name=name,
                    permission=permission,
                    description=description,
                    input_schema=input_schema
                )

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
            print(type(response))

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
        self.mcp_thread.join()
