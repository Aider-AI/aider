from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from aider.mcp.mcp_tool import McpTool

@dataclass
class McpServer:
    """Represents an MCP server configuration."""
    name: str
    command: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    tools: Dict[str, McpTool] = field(default_factory=dict)

    def add_tool(self, tool_name: str, permission: str = "manual", description: Optional[str] = None,
                 input_schema: Optional[Dict[str, Any]] = None) -> None:
        """Add a tool to this server."""
        self.tools[tool_name] = McpTool(tool_name, permission, description, input_schema)

    def set_tool_permission(self, tool_name: str, permission: str) -> bool:
        """Set the permission for a tool. Returns True if successful, False if tool not found."""
        if tool_name in self.tools:
            self.tools[tool_name].permission = permission
            return True
        return False

    def get_env_dict(self) -> Dict[str, str]:
        """Get a dictionary of environment variables for this server."""
        return self.env_vars

    def is_valid(self) -> bool:
        """Check if the server configuration is valid.
        """
        return self.command is not None
