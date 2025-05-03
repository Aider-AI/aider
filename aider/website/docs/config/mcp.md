---
parent: Configuration
nav_order: 120
description: Configure Model Control Protocol (MCP) servers for enhanced AI capabilities.
---

# Model Control Protocol (MCP)

Model Control Protocol (MCP) servers extend aider's capabilities by providing additional tools and functionality to the AI models. MCP servers can add features like git operations, context retrieval, and other specialized tools.

## Configuring MCP Servers

Aider supports configuring MCP servers using the MCP Server Configuration schema. Please
see the [Model Context Protocol documentation](https://modelcontextprotocol.io/introduction)
for more information.

You have two ways of sharing your MCP server configuration with Aider.

### 1. Using a JSON string

You can specify MCP servers directly on the command line using the `--mcp-servers` option with a JSON string:

```bash
aider --mcp-servers '{"mcpServers":{"git":{"command":"uvx","args":["mcp-server-git"]}}}'
```

### 2. Using a configuration file

Alternatively, you can store your MCP server configurations in a JSON file and reference it with the `--mcp-servers-file` option:

```bash
aider --mcp-servers-file mcp.json
```

Example `mcp.json` file:

```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    }
  }
}
```

## YAML Configuration

You can also configure MCP servers in your `.aider.conf.yml` file:

```yaml
mcp-servers: |
  {
    "mcpServers": {
      "git": {
        "command": "uvx",
        "args": ["mcp-server-git"]
      }
    }
  }
```

Or specify a configuration file:

```yaml
mcp-servers-file: /path/to/mcp.json
```

These options are configurable in any of Aider's config file formats.

## Environment Variables

You can also configure MCP servers using environment variables in your `.env` file:

```
AIDER_MCP_SERVERS={"mcpServers":{"git":{"command":"uvx","args":["mcp-server-git"]}}}
```

Or specify a configuration file:

```
AIDER_MCP_SERVERS_FILE=/path/to/mcp.json
```

## Troubleshooting

If you encounter issues with MCP servers:

1. Use the `--verbose` flag to see detailed information about MCP server loading
2. Check that the specified executables are installed and available in your PATH
3. Verify that your JSON configuration is valid

For more information about specific MCP servers and their capabilities, refer to their respective documentation.
