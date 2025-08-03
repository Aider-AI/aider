import asyncio
import logging
import os
from contextlib import AsyncExitStack

import aiohttp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpServer:
    """
    A client for MCP servers that provides tools to Aider coders. An McpServer class
    is initialized per configured MCP Server

    Current usage:

        conn = await session.connect()  # Use connect() directly
        tools = await experimental_mcp_client.load_mcp_tools(session=s, format="openai")
        await session.disconnect()
        print(tools)
    """

    def __init__(self, server_config):
        """Initialize the MCP tool provider.

        Args:
            server_config: Configuration for the MCP server
        """
        self.config = server_config
        self.name = server_config.get("name", "unnamed-server")
        self.session = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """Connect to the MCP server and return the session.

        If a session is already active, returns the existing session.
        Otherwise, establishes a new connection and initializes the session.

        Returns:
            ClientSession: The active session
        """
        if self.session is not None:
            logging.info(f"Using existing session for MCP server: {self.name}")
            return self.session

        logging.info(f"Establishing new connection to MCP server: {self.name}")
        command = self.config["command"]
        server_params = StdioServerParameters(
            command=command,
            args=self.config.get("args"),
            env={**os.environ, **self.config["env"]} if self.config.get("env") else None,
        )

        try:
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
            return session
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.disconnect()
            raise

    async def disconnect(self):
        """Disconnect from the MCP server and clean up resources."""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.stdio_context = None
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")

class HttpStreamingServer(McpServer):
    def __init__(self, server_config):
        super().__init__(server_config)
        self.aiohttp_session = None

    async def connect(self):
        if self.session is not None:
            logging.info(f"Using existing session for MCP server: {self.name}")
            return self.session

        logging.info(f"Establishing new connection to MCP server: {self.name}")
        
        self.aiohttp_session = aiohttp.ClientSession()
        await self.exit_stack.enter_async_context(self.aiohttp_session)

        try:
            url = self.config["url"]
            response = await self.aiohttp_session.post(url, data=b"")
            response.raise_for_status()
            
            async def read_gen():
                async for chunk in response.content.iter_any():
                    yield chunk
            
            read = read_gen()

            async def write(data):
                await self.aiohttp_session.post(url, data=data)

            self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            return self.session
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.disconnect()
            raise

