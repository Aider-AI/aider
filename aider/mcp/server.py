import asyncio
import logging
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


class McpServer:
    """
    A client for MCP servers that provides tools to Aider coders. An McpServer class
    is initialized per configured MCP Server

    Uses the mcp library to create and initialize ClientSession objects.
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
            os.makedirs(".aider/logs/", exist_ok=True)
            with open(".aider/logs/mcp-errors.log", "w") as err_file:
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params, errlog=err_file)
                )
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
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")


class HttpStreamingServer(McpServer):
    """HTTP streaming MCP server using mcp.client.streamablehttp_client."""

    async def connect(self):
        if self.session is not None:
            logging.info(f"Using existing session for MCP server: {self.name}")
            return self.session

        logging.info(f"Establishing new connection to HTTP MCP server: {self.name}")
        try:
            url = self.config.get("url")
            headers = self.config.get("headers", {})
            http_transport = await self.exit_stack.enter_async_context(
                streamablehttp_client(url, headers=headers)
            )
            read, write, _response = http_transport

            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
            return session
        except Exception as e:
            logging.error(f"Error initializing HTTP server {self.name}: {e}")
            await self.disconnect()
            raise


class SseServer(McpServer):
    """SSE (Server-Sent Events) MCP server using mcp.client.sse_client."""

    async def connect(self):
        if self.session is not None:
            logging.info(f"Using existing session for SSE MCP server: {self.name}")
            return self.session

        logging.info(f"Establishing new connection to SSE MCP server: {self.name}")
        try:
            url = self.config.get("url")
            headers = self.config.get("headers", {})
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(url, headers=headers)
            )
            read, write, _response = sse_transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
            return session
        except Exception as e:
            logging.error(f"Error initializing SSE server {self.name}: {e}")
            await self.disconnect()
            raise


class LocalServer(McpServer):
    """
    A dummy McpServer for executing local, in-process tools
    that are not provided by an external MCP server.
    """

    async def connect(self):
        """Local tools don't need a connection."""
        if self.session is not None:
            logging.info(f"Using existing session for local tools: {self.name}")
            return self.session

        self.session = object()  # Dummy session object
        return self.session

    async def disconnect(self):
        """Disconnect from the MCP server and clean up resources."""
        self.session = None
