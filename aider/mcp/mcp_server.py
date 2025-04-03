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

    def set_tool(
            self,
            tool_name: str,
            permission: str = "manual",
            description: Optional[str] = None,
            input_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing tool's description and input schema."""
        if tool_name in self.tools:
            if description is not None:
                self.tools[tool_name].description = description
            if input_schema is not None:
                self.tools[tool_name].input_schema = input_schema
            if permission is not None:
                self.tools[tool_name].permission = permission
        else:
            self.tools[tool_name] = McpTool(tool_name, permission, description, input_schema)

    def get_env_dict(self) -> Dict[str, str]:
        """Get a dictionary of environment variables for this server."""
        return self.env_vars

    def is_valid(self) -> bool:
        """Check if the server configuration is valid.
        """
        return self.command is not None
