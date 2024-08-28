import importlib
import os
import warnings
from typing import Any

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

AIDER_SITE_URL = "https://aider.chat"
AIDER_APP_NAME = "Aider"

os.environ["OR_SITE_URL"] = AIDER_SITE_URL
os.environ["OR_APP_NAME"] = AIDER_APP_NAME

class LazyLiteLLM:
    """
    A lazy-loading wrapper for the litellm module to improve startup time.
    """
    
    def __init__(self):
        self._lazy_module = None

    def __getattr__(self, name: str) -> Any:
        if name == "_lazy_module":
            return super().__getattribute__(name)
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self) -> None:
        if self._lazy_module is not None:
            return

        try:
            self._lazy_module = importlib.import_module("litellm")
            self._lazy_module.suppress_debug_info = True
            self._lazy_module.set_verbose = False
            self._lazy_module.drop_params = True
        except ImportError:
            raise ImportError("Failed to import litellm. Please ensure it's installed.")

litellm = LazyLiteLLM()

__all__ = ["litellm"]
