from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class McpTool:
    """Represents an MCP tool with its name and permission settings."""
    name: str
    permission: str = "manual"  # "manual" or "auto"
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
