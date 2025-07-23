import os
import re
from typing import Dict, Optional, List, Any # Ensure Any is imported

class MCPServerConfig:
    def __init__(self,
                 name: str,  # Name will be passed in from the dict key
                 command: Optional[str] = None,
                 args: Optional[List[str]] = None,
                 url: Optional[str] = None, # For potential HTTP/S servers
                 env: Optional[Dict[str, str]] = None,
                 requires_confirmation: Optional[List[str]] = None,
                 enabled: bool = True, # Default to True as per example
                 exclude_tools: Optional[List[str]] = None,
                 description: Optional[str] = None,
                 auth_config: Optional[Dict[str, Any]] = None): # Added auth_config

        self.name: str = name # Used in _get_env_var for warning messages

        # Substitute environment variables before assigning to self
        self.url = self._substitute_env_vars(url) if url else None
        self.command = self._substitute_env_vars(command) if command else None

        # For args list, substitute each item
        self.args: List[str] = [self._substitute_env_vars(arg) for arg in args] if args is not None else []

        # For env dict, substitute each value
        self.env: Dict[str, str] = {k: self._substitute_env_vars(v) for k, v in env.items()} if env is not None else {}

        self.requires_confirmation: List[str] = requires_confirmation if requires_confirmation is not None else []
        self.enabled: bool = enabled
        self.exclude_tools: List[str] = exclude_tools if exclude_tools is not None else []
        self.description: Optional[str] = description

        # For auth_config dict, substitute each value recursively
        self.auth_config: Optional[Dict[str, Any]] = self._substitute_env_vars(auth_config) if auth_config else None

        self.protocol: Optional[str] = None
        self._determine_protocol_and_validate()

    def _get_env_var(self, var_name: str, original_placeholder: str) -> str:
        var_value = os.getenv(var_name)
        if var_value is None:
            # It's important that self.name is already set before this method is called by _substitute_env_vars
            # which it is, as self.name is the first assignment in __init__.
            print(f"Warning: Environment variable '{var_name}' not found for MCP config '{self.name}'. Placeholder '{original_placeholder}' will be used.")
            return original_placeholder
        return var_value

    def _substitute_env_vars(self, value: Any) -> Any:
        if isinstance(value, str):
            # Pattern for ${VAR_NAME}
            value = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}',
                           lambda m: self._get_env_var(m.group(1), m.group(0)),
                           value)
            # Pattern for $VAR_NAME (more robust version with lookahead for word boundary)
            value = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])',
                           lambda m: self._get_env_var(m.group(1), m.group(0)),
                           value)
            return value
        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        return value

    def _determine_protocol_and_validate(self) -> None:
        if self.command:
            self.protocol = "stdio"
            if not isinstance(self.args, list):
                raise ValueError(f"MCP Server '{self.name}': 'args' must be a list for stdio protocol.")
        elif self.url:
            if self.url.startswith("http://"):
                self.protocol = "http"
            elif self.url.startswith("https://"):
                self.protocol = "https"
            else:
                raise ValueError(f"MCP Server '{self.name}': Invalid URL scheme for 'url'. Must be http or https. Got: {self.url}")
        else:
            pass # Protocol remains None, connection will fail

    def __repr__(self) -> str:
        return (f"MCPServerConfig(name='{self.name}', protocol='{self.protocol}', "
                f"enabled={self.enabled}, command='{self.command}', args={self.args}, url='{self.url}')")
