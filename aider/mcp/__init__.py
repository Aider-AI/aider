import json

from aider.mcp.server import HttpStreamingServer, McpServer


def _parse_mcp_servers_from_json_string(json_string, io, verbose=False, mcp_transport="stdio"):
    """Parse MCP servers from a JSON string."""
    servers = []

    try:
        config = json.loads(json_string)
        if verbose:
            io.tool_output("Loading MCP servers from provided JSON string")

        if "mcpServers" in config:
            for name, server_config in config["mcpServers"].items():
                if verbose:
                    io.tool_output(f"Loading MCP server: {name}")

                # Create a server config with name included
                server_config["name"] = name
                transport = server_config.get("transport", mcp_transport)
                if transport == "stdio":
                    servers.append(McpServer(server_config))
                elif transport == "http":
                    servers.append(HttpStreamingServer(server_config))

            if verbose:
                io.tool_output(f"Loaded {len(servers)} MCP servers from JSON string")
            return servers
        else:
            io.tool_warning("No 'mcpServers' key found in MCP config JSON string")
    except json.JSONDecodeError:
        io.tool_error("Invalid JSON in MCP config string")
    except Exception as e:
        io.tool_error(f"Error loading MCP config from string: {e}")

    return servers


def _parse_mcp_servers_from_file(file_path, io, verbose=False, mcp_transport="stdio"):
    """Parse MCP servers from a JSON file."""
    servers = []

    try:
        with open(file_path, "r") as f:
            config = json.load(f)

        if verbose:
            io.tool_output(f"Loading MCP servers from file: {file_path}")

        if "mcpServers" in config:
            for name, server_config in config["mcpServers"].items():
                if verbose:
                    io.tool_output(f"Loading MCP server: {name}")

                # Create a server config with name included
                server_config["name"] = name
                transport = server_config.get("transport", mcp_transport)
                if transport == "stdio":
                    servers.append(McpServer(server_config))
                elif transport == "http":
                    servers.append(HttpStreamingServer(server_config))

            if verbose:
                io.tool_output(f"Loaded {len(servers)} MCP servers from {file_path}")
            return servers
        else:
            io.tool_warning(f"No 'mcpServers' key found in MCP config file: {file_path}")
    except FileNotFoundError:
        io.tool_warning(f"MCP config file not found: {file_path}")
    except json.JSONDecodeError:
        io.tool_error(f"Invalid JSON in MCP config file: {file_path}")
    except Exception as e:
        io.tool_error(f"Error loading MCP config from file: {e}")

    return servers


def load_mcp_servers(mcp_servers, mcp_servers_file, io, verbose=False, mcp_transport="stdio"):
    """Load MCP servers from a JSON string or file."""
    servers = []

    # First try to load from the JSON string (preferred)
    if mcp_servers:
        servers = _parse_mcp_servers_from_json_string(mcp_servers, io, verbose, mcp_transport)
        if servers:
            return servers

    # If JSON string failed or wasn't provided, try the file
    if mcp_servers_file:
        servers = _parse_mcp_servers_from_file(mcp_servers_file, io, verbose, mcp_transport)

    return servers
