import importlib
import json
import os
import warnings
from pathlib import Path

from aider.dump import dump  # noqa: F401

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

AIDER_SITE_URL = "https://aider.chat"
AIDER_APP_NAME = "Aider"

os.environ["OR_SITE_URL"] = AIDER_SITE_URL
os.environ["OR_APP_NAME"] = AIDER_APP_NAME
os.environ["LITELLM_MODE"] = "PRODUCTION"

# `import litellm` takes 1.5 seconds, defer it!

VERBOSE = False

# Patch json.load to handle UTF-8 encoding for litellm
original_json_load = json.load

def patched_json_load(fp, *args, **kwargs):
    try:
        # First try the original method
        return original_json_load(fp, *args, **kwargs)
    except UnicodeDecodeError:
        # If it fails with UnicodeDecodeError, try with UTF-8 encoding
        try:
            # Read the file content with UTF-8 encoding
            content = Path(fp.name).read_text(encoding='utf-8')
            # Parse the content as JSON
            return json.loads(content, *args, **kwargs)
        except Exception:
            # If that also fails, re-raise the original exception
            raise

# Apply the monkey patch
json.load = patched_json_load


class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return

        if VERBOSE:
            print("Loading litellm...")

        self._lazy_module = importlib.import_module("litellm")

        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()


litellm = LazyLiteLLM()

__all__ = [litellm]
