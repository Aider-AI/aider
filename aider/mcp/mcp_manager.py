import asyncio # For async operations
from typing import Dict, List, Optional, Tuple, Any

# Assuming MCPServerConfig is in mcp_config.py
from .mcp_config import MCPServerConfig

from mcp import ClientSession, types as mcp_types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
# from mcp.exceptions import MCPError # Example if SDK has specific errors

class MCPConnectedServer:
    def __init__(self, config: MCPServerConfig):
        self.config: MCPServerConfig = config
        self.session: Optional[ClientSession] = None # Changed
        self.last_error: Optional[str] = None
        self.status: str = "disconnected"

        self.resources: List[mcp_types.ResourceDefinition] = [] # Changed
        self.tools: List[mcp_types.ToolDefinition] = [] # Changed
        self.prompts: List[mcp_types.PromptDefinition] = [] # Changed

    async def connect(self) -> bool:
        self.status = "connecting"
        self.last_error = None
        print(f"INFO: Attempting to connect to MCP server '{self.config.name}' at {self.config.url}...")

        try:
            read_stream = None
            write_stream = None
            # These context managers should handle closing streams if session creation fails

            if self.config.protocol == "stdio":
                if not self.config.command or not isinstance(self.config.command, list) or len(self.config.command) == 0:
                    raise ValueError("Stdio command not properly configured.")

                # Conceptual placeholder for StdioServerParameters:
                # params = StdioServerParameters(
                #     command=self.config.command[0],
                #     args=self.config.command[1:],
                #     env=self.config.env # TODO: Ensure this is passed to the SDK
                # )
                params = StdioServerParameters(command=self.config.command[0], args=self.config.command[1:])
                # The stdio_client itself is the async context manager
                # We need to manage its lifecycle carefully with the session
                # This might require restructuring if stdio_client needs to be held open by MCPConnectedServer
                # For now, let's assume we can get streams and pass to session
                # This is a common pattern: client resources are passed to session

                # Simulating how streams might be obtained and session created.
                # The actual SDK usage might differ in how streams/client are managed.
                # This is a complex part, SDK docs are key here.
                # Let's assume a simplified acquisition for now for the subtask
                # and refine if SDK structure is different.

                # If stdio_client is an async context manager that yields streams:
                # async with stdio_client(params) as (rs, ws):
                #    self.session = ClientSession(rs, ws)
                #    await self.session.initialize()

                # This is a placeholder for the complex stream management with stdio_client
                # For the subtask, we'll assume it can be simplified to getting a session
                # In reality, the stdio_client might need to be an attribute of MCPConnectedServer
                # if its lifetime is tied to the connection.
                print(f"INFO: Establishing stdio connection for '{self.config.name}' (conceptual)...")
                # STUB for stdio_client usage - will be complex
                # For now, to make progress, simulate a successful setup for stdio
                # if we were to proceed with actual SDK, this needs detailed SDK consultation
                if self.config.url == "stdio:dummy_success_placeholder": # Test condition
                     self.session = ClientSession(None, None) # Dummy session for placeholder
                     print("INFO: stdio dummy session initialized for placeholder.")
                else: # Simulate failure for other stdio for now
                     raise NotImplementedError("Actual stdio_client integration requires careful SDK usage review.")

            elif self.config.protocol in ("http", "https"):
                if not self.config.http_url:
                    raise ValueError("HTTP/S URL not configured.")
                # Similarly, streamablehttp_client is an async context manager
                # Conceptual placeholder for streamablehttp_client call:
                # async with streamablehttp_client(
                #     self.config.http_url,
                #     # TODO: Pass SSL verification preference, e.g.,
                #     # ssl_verify=get_aider_global_ssl_verify_setting()
                # ) as (rs, ws, _resp):
                #    self.session = ClientSession(rs, ws)
                #    await self.session.initialize()
                print(f"INFO: Establishing HTTP/S connection for '{self.config.name}' (conceptual)...")
                # STUB for streamablehttp_client usage
                if "dummy_success_placeholder" in self.config.http_url : # Test condition
                    self.session = ClientSession(None,None) # Dummy session for placeholder
                    print("INFO: http dummy session initialized for placeholder.")
                else: # Simulate failure for other http for now
                    raise NotImplementedError("Actual streamablehttp_client integration requires careful SDK usage review.")


            # If session was created (even if dummy for now)
            if self.session:
                # await self.session.initialize() # Actual SDK call - this might be part of ClientSession constructor or specific method
                print(f"INFO: Successfully initialized session with '{self.config.name}'.")
                await self.fetch_capabilities()
                if self.last_error:
                    self.status = "error"
                    print(f"ERROR: Connected to '{self.config.name}' but failed to fetch capabilities: {self.last_error}")
                    # await self.disconnect() # clean up session
                    return False
                self.status = "connected"
                print(f"INFO: Successfully connected to MCP server '{self.config.name}'.")
                return True
            else: # Should not happen if above logic raises or sets session
                raise Exception("Session not created despite connection attempt.")

        except NotImplementedError as nie: # Catch our temporary NIEs
            self.last_error = str(nie)
            self.status = "error"
            self.session = None
            print(f"ERROR: Connecting to '{self.config.name}' (NotImplemented): {self.last_error}")
            return False
        except Exception as e:
            self.last_error = f"Error connecting to '{self.config.name}': {type(e).__name__} - {e}"
            self.status = "error"
            if self.session: # If session was created but something else failed
                try:
                    await self.session.close()
                except: pass # Best effort to close
            self.session = None
            print(f"ERROR: Detail: {self.last_error}")
            return False

    async def disconnect(self) -> None:
        print(f"INFO: Disconnecting from MCP server '{self.config.name}'...")
        if self.session:
            try:
                await self.session.close() # Actual SDK call
            except Exception as e:
                self.last_error = f"Error during disconnect: {e}"
                # self.status should be 'disconnected' anyway
                print(f"ERROR: Disconnecting from '{self.config.name}': {self.last_error}")
            self.session = None
        self.status = "disconnected"
        print(f"INFO: Disconnected from '{self.config.name}'.")


    async def fetch_capabilities(self) -> None:
        if not self.session:
            self.last_error = "Cannot fetch capabilities: not connected."
            return

        print(f"INFO: Fetching capabilities for '{self.config.name}'...")
        self.last_error = None
        try:
            # Hypothetical specific SDK errors
            # Replace with actual SDK error types if known e.g. from mcp.exceptions import MCPAuthError, etc.
            # class MCPAuthError(Exception): pass
            # class MCPConnectionError(Exception): pass
            # class MCPTimeoutError(Exception): pass

            # Add comment about potential timeout for the whole operation
            # For example: await asyncio.wait_for(self._do_fetch_capabilities(), timeout=FETCH_TIMEOUT)
            self.resources = await self.session.list_resources()
            self.tools = await self.session.list_tools()
            self.prompts = await self.session.list_prompts()
            print(f"INFO: Successfully fetched {len(self.resources)} resources, {len(self.tools)} tools, {len(self.prompts)} prompts for '{self.config.name}'.")
        # except MCPAuthError as e:
        #     self.last_error = f"Authentication error fetching capabilities: {e}"
        #     print(f"ERROR: Auth error for '{self.config.name}': {self.last_error}")
        # except MCPConnectionError as e:
        #     self.last_error = f"Connection error fetching capabilities: {e}"
        #     print(f"ERROR: Connection error for '{self.config.name}': {self.last_error}")
        # except MCPTimeoutError as e:
        #     self.last_error = f"Timeout error fetching capabilities: {e}"
        #     print(f"ERROR: Timeout for '{self.config.name}': {self.last_error}")
        except Exception as e: # Generic fallback
            self.last_error = f"Generic error fetching capabilities: {type(e).__name__} - {e}"
            print(f"ERROR: Generic error for '{self.config.name}' during fetch_capabilities: {self.last_error}")

        if self.last_error: # If any error occurred
            self.resources = []
            self.tools = []
            self.prompts = []
            # Note: self.status is not changed here; caller (connect or rescan) handles status.


    async def read_resource_content(self, resource_uri: str) -> Optional[Tuple[str, str]]: # (content_str, mime_type)
        if not self.session:
            self.last_error = "Not connected"
            print(f"ERROR: Cannot read resource '{resource_uri}' from '{self.config.name}': Not connected.")
            return None

        print(f"INFO: Reading resource '{resource_uri}' from '{self.config.name}'...")
        self.last_error = None
        try:
            # Conceptual: Add timeout for SDK call if needed
            # content_bytes, mime_type = await asyncio.wait_for(
            #    self.session.read_resource(resource_uri),
            #    timeout=self.config.get("read_timeout_seconds", 30) # Example: get timeout from config
            # )
            content_bytes, mime_type = await self.session.read_resource(resource_uri)

            content_str: str
            # Attempt to decode known text types, default to UTF-8 for others.
            # This could be expanded with a more comprehensive mime_type check.
            if mime_type.startswith("text/"):
                try:
                    # Try common encodings if specific charset isn't in mime_type
                    # For simplicity, just trying utf-8. A real app might check mime_type for charset.
                    content_str = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content_str = content_bytes.decode('latin-1') # Fallback for some cases
                    except UnicodeDecodeError:
                        print(f"WARNING: Could not decode resource '{resource_uri}' (mime: {mime_type}) as UTF-8 or Latin-1. Content may be binary or an unsupported text encoding.")
                        # Represent binary or undecodable content as a placeholder or error message.
                        # For now, returning a placeholder. Aider primarily handles text.
                        content_str = f"[Undecodable content: {mime_type}]"
            elif mime_type in ("application/json", "application/xml", "application/javascript", "application/yaml"): # Add other text-based application types
                 try:
                    content_str = content_bytes.decode('utf-8')
                 except UnicodeDecodeError:
                    content_str = f"[Undecodable JSON/XML/etc. content: {mime_type}]"
            else:
                # For non-text or unknown types, indicate it's binary or provide a generic message.
                print(f"INFO: Resource '{resource_uri}' has non-primary-text mime_type '{mime_type}'. Treating as binary/opaque.")
                content_str = f"[Content of type '{mime_type}', not displayed as text]"

            print(f"INFO: Successfully read resource '{resource_uri}' (mime: {mime_type}) from '{self.config.name}'.")
            return content_str, mime_type
            # Hypothetical specific SDK errors
            # except mcp_types.MCPAuthError as e:
            #     self.last_error = f"Authentication error reading resource {resource_uri}: {e}"
            # except mcp_types.MCPConnectionError as e:
            #     self.last_error = f"Connection error reading resource {resource_uri}: {e}"
            # except mcp_types.MCPTimeoutError as e: # If asyncio.TimeoutError is not used
            #     self.last_error = f"Timeout reading resource {resource_uri}: {e}"
            # except asyncio.TimeoutError: # If using asyncio.wait_for
            #     self.last_error = f"Timeout reading resource {resource_uri}"
        except Exception as e: # Generic fallback
            self.last_error = f"Generic error reading resource {resource_uri}: {type(e).__name__} - {e}"

        if self.last_error:
            print(f"ERROR: Reading resource '{resource_uri}' from '{self.config.name}': {self.last_error}")
            return None

        print(f"INFO: Successfully read resource '{resource_uri}' (mime: {mime_type}) from '{self.config.name}'.")
        return content_str, mime_type


    async def execute_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        if not self.session:
            self.last_error = "Not connected"
            print(f"ERROR: Cannot execute tool '{tool_name}' on '{self.config.name}': Not connected.")
            return None

        print(f"INFO: Executing MCP tool '{tool_name}' with args {arguments} on server '{self.config.name}'...")
        self.last_error = None
        try:
            # Conceptual: Add timeout for SDK call if needed
            # result = await asyncio.wait_for(
            #    self.session.call_tool(tool_name=tool_name, arguments=arguments),
            #    timeout=self.config.get("tool_timeout_seconds", 60) # Example
            # )
            result = await self.session.call_tool(tool_name=tool_name, arguments=arguments)

            print(f"INFO: Successfully executed MCP tool '{tool_name}' on '{self.config.name}'. Result: {result}")
            return result
        # except mcp_types.MCPAuthError as e:
        #     self.last_error = f"Authentication error executing tool {tool_name}: {e}"
        # except mcp_types.MCPConnectionError as e:
        #     self.last_error = f"Connection error executing tool {tool_name}: {e}"
        # except mcp_types.MCPTimeoutError as e: # If asyncio.TimeoutError is not used
        #     self.last_error = f"Timeout executing tool {tool_name}: {e}"
        # except asyncio.TimeoutError: # If using asyncio.wait_for
        #     self.last_error = f"Timeout executing tool {tool_name}"
        except Exception as e: # Generic fallback
            self.last_error = f"Generic error executing tool {tool_name}: {type(e).__name__} - {e}"

        if self.last_error:
            print(f"ERROR: Executing MCP tool '{tool_name}' on '{self.config.name}': {self.last_error}")
            return None

class MCPManager:
    def __init__(self, mcp_server_configs: List[MCPServerConfig]):
        # This expects a list of MCPServerConfig objects,
        # which would be populated by process_mcp_configurations in args.py
        # and then passed to this manager when it's instantiated.
        self.server_configs_map: Dict[str, MCPServerConfig] = {
            conf.name: conf for conf in mcp_server_configs
        }
        self.connected_servers: Dict[str, MCPConnectedServer] = {}
        print(f"INFO: MCPManager initialized with {len(mcp_server_configs)} server configurations.")

    async def connect_server(self, server_name: str) -> bool:
        if server_name not in self.server_configs_map:
            print(f"ERROR: Cannot connect, server name '{server_name}' not configured.")
            return False

        if server_name in self.connected_servers and self.connected_servers[server_name].status == "connected":
            print(f"INFO: Server '{server_name}' is already connected.")
            return True

        config = self.server_configs_map[server_name]
        connected_server = MCPConnectedServer(config)
        self.connected_servers[server_name] = connected_server # Store it even if connection fails to see status

        if await connected_server.connect():
            return True
        else:
            # connect() method already prints errors
            return False

    async def connect_all_enabled_servers(self) -> None:
        print("INFO: Attempting to connect to all enabled MCP servers...")
        for name, config in self.server_configs_map.items():
            if config.enabled:
                if name not in self.connected_servers or self.connected_servers[name].status != "connected":
                    await self.connect_server(name)
            else:
                print(f"INFO: Server '{name}' is disabled in configuration, skipping connection.")
        print("INFO: Finished attempting connections to enabled MCP servers.")


    async def disconnect_server(self, server_name: str) -> None:
        if server_name in self.connected_servers:
            server = self.connected_servers.pop(server_name) # Remove it after getting
            await server.disconnect()
        else:
            print(f"INFO: Server '{server_name}' not found or not connected, cannot disconnect.")

    async def disconnect_all_servers(self) -> None:
        print("INFO: Disconnecting all MCP servers...")
        server_names = list(self.connected_servers.keys()) # Avoid issues with dict size change during iteration
        for name in server_names:
            await self.disconnect_server(name)
        print("INFO: All MCP servers disconnected.")

    def get_server_status(self, server_name: str) -> Optional[str]:
        if server_name in self.connected_servers:
            return self.connected_servers[server_name].status
        elif server_name in self.server_configs_map:
            return "disconnected" # It's configured but not in connected_servers
        return None # Not configured

    def get_server_last_error(self, server_name: str) -> Optional[str]:
        if server_name in self.connected_servers:
            return self.connected_servers[server_name].last_error
        return None

    def get_all_server_statuses(self) -> List[Dict[str, Any]]:
        statuses = []
        for name, config in self.server_configs_map.items():
            status_info = {
                "name": name,
                "url": config.url,
                "description": config.description,
                "configured_enabled": config.enabled,
                "status": "disconnected", # Default if not in connected_servers
                "last_error": None,
            }
            if name in self.connected_servers:
                server_instance = self.connected_servers[name]
                status_info["status"] = server_instance.status
                status_info["last_error"] = server_instance.last_error
            statuses.append(status_info)
        return statuses

    async def refresh_server_capabilities(self, server_name: str) -> bool:
        if server_name in self.connected_servers:
            server = self.connected_servers[server_name]
            if server.status == "connected":
                await server.fetch_capabilities()
                return server.last_error is None # True if no error during fetch
            else:
                print(f"ERROR: Server '{server_name}' is not connected. Cannot refresh capabilities.")
                return False
        else:
            print(f"ERROR: Server '{server_name}' not found. Cannot refresh capabilities.")
            return False

    async def refresh_all_connected_servers_capabilities(self) -> None:
        print("INFO: Refreshing capabilities for all connected MCP servers...")
        for name, server in self.connected_servers.items():
            if server.status == "connected":
                print(f"INFO: Refreshing capabilities for '{name}'...")
                await server.fetch_capabilities()
            else:
                print(f"INFO: Server '{name}' not connected, skipping capability refresh.")
        print("INFO: Finished refreshing capabilities for all connected MCP servers.")


    def get_all_tools(self) -> List[Tuple[MCPServerConfig, mcp_types.ToolDefinition]]:
        """Returns a list of all tools from all connected and enabled servers."""
        all_tools: List[Tuple[MCPServerConfig, mcp_types.ToolDefinition]] = []
        for server_name, connected_server in self.connected_servers.items():
            if connected_server.config.enabled and connected_server.status == "connected":
                for tool_def in connected_server.tools:
                    all_tools.append((connected_server.config, tool_def))
        return all_tools

    def get_all_resources(self) -> List[Tuple[MCPServerConfig, mcp_types.ResourceDefinition]]:
        """Returns a list of all resources from all connected and enabled servers."""
        all_resources: List[Tuple[MCPServerConfig, mcp_types.ResourceDefinition]] = []
        for server_name, connected_server in self.connected_servers.items():
            if connected_server.config.enabled and connected_server.status == "connected":
                for res_def in connected_server.resources:
                    all_resources.append((connected_server.config, res_def))
        return all_resources

    async def read_mcp_resource(self, server_name: str, resource_uri: str) -> Optional[Tuple[str, str]]:
        server = self.connected_servers.get(server_name)
        if not server:
            print(f"ERROR: Server '{server_name}' not found for read_mcp_resource.")
            return None
        if server.status != "connected":
            print(f"ERROR: Server '{server_name}' is not connected (status: {server.status}). Cannot read resource '{resource_uri}'.")
            return None

        result = await server.read_resource_content(resource_uri)
        if result is None:
            # server.last_error should be set by MCPConnectedServer method
            print(f"ERROR: Failed to read resource '{resource_uri}' from '{server_name}'. Server error: {server.last_error or 'Unknown error within server method.'}")
        return result

    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Optional[Any]:
        server = self.connected_servers.get(server_name)
        if not server:
            print(f"ERROR: Server '{server_name}' not found for call_mcp_tool.")
            return None
        if server.status != "connected":
            print(f"ERROR: Server '{server_name}' is not connected (status: {server.status}). Cannot call tool '{tool_name}'.")
            return None

        result = await server.execute_mcp_tool(tool_name, arguments)
        if result is None:
            # server.last_error should be set by MCPConnectedServer method
            print(f"ERROR: Failed to execute tool '{tool_name}' on '{server_name}'. Server error: {server.last_error or 'Unknown error within server method.'}")
        return result
            return None
