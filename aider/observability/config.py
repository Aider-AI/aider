"""
Configuration for Observability Module
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ObservabilityConfig:
    """Configuration for observability features"""
    
    # LangSmith settings
    langsmith_enabled: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "aider-observability"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    
    # Local metrics settings
    local_metrics_enabled: bool = True
    metrics_db_path: Optional[str] = None
    
    # Performance settings
    async_logging: bool = False  # Future: async metric logging
    batch_size: int = 10  # Future: batch metric writes
    
    # Retention settings
    metrics_retention_days: int = 30
    
    @classmethod
    def from_environment(cls) -> "ObservabilityConfig":
        """
        Create configuration from environment variables
        
        Environment variables:
        - LANGSMITH_API_KEY: LangSmith API key
        - LANGSMITH_PROJECT: Project name (default: "aider-observability")
        - AIDER_OBSERVABILITY_ENABLED: Enable observability (default: true)
        """
        langsmith_api_key = os.environ.get("LANGSMITH_API_KEY")
        langsmith_enabled = bool(langsmith_api_key)
        
        return cls(
            langsmith_enabled=langsmith_enabled,
            langsmith_api_key=langsmith_api_key,
            langsmith_project=os.environ.get("LANGSMITH_PROJECT", "aider-observability"),
            local_metrics_enabled=os.environ.get("AIDER_OBSERVABILITY_ENABLED", "true").lower() == "true"
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.langsmith_enabled and not self.langsmith_api_key:
            return False
        return True


# Global configuration instance
_config = None

def get_config() -> ObservabilityConfig:
    """Get or create global configuration"""
    global _config
    if _config is None:
        _config = ObservabilityConfig.from_environment()
    return _config

def set_config(config: ObservabilityConfig):
    """Set global configuration"""
    global _config
    _config = config