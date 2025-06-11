from typing import Dict, Optional, List # Add List here

class MCPServerConfig:
    def __init__(self, name: str, url: str, enabled: bool = True, auth_config: Optional[Dict] = None, description: Optional[str] = None): # Add description
        self.name: str = name
        self.url: str = url
        self.enabled: bool = enabled
        self.auth_config: Optional[Dict] = auth_config
        self.description: Optional[str] = description # Add description

        self.protocol: str
        self.command: Optional[List[str]] = None # For stdio
        self.http_url: Optional[str] = None # For http/https

        self._parse_url()

    def _parse_url(self) -> None:
        if self.url.startswith("stdio:"):
            self.protocol = "stdio"
            # Basic parsing: assumes command and args are space-separated after "stdio:"
            # More robust parsing might be needed for complex commands with spaces in args.
            parts = self.url[len("stdio:"):].strip().split(' ')
            self.command = [part for part in parts if part] # Filter out empty strings
            if not self.command:
                raise ValueError(f"Invalid stdio URL format for MCP server '{self.name}': command missing.")
        elif self.url.startswith("http://") or self.url.startswith("https://"):
            self.protocol = "https" if self.url.startswith("https://") else "http"
            self.http_url = self.url
        else:
            raise ValueError(f"Unsupported URL scheme for MCP server '{self.name}': {self.url}. Must start with 'stdio:', 'http://', or 'https://'.")

    def __repr__(self) -> str:
        return f"MCPServerConfig(name='{self.name}', url='{self.url}', enabled={self.enabled}, protocol='{self.protocol}')"
