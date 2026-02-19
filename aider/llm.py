import importlib
import os
import warnings

from aider.dump import dump  # noqa: F401

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

AIDER_SITE_URL = "https://aider.chat"
AIDER_APP_NAME = "Aider"

os.environ["OR_SITE_URL"] = AIDER_SITE_URL
os.environ["OR_APP_NAME"] = AIDER_APP_NAME
os.environ["LITELLM_MODE"] = "PRODUCTION"

# `import litellm` takes 1.5 seconds, defer it!

VERBOSE = False


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

        try:
            self._lazy_module = importlib.import_module("litellm")
        except (ImportError, ModuleNotFoundError) as e:
            # Handle missing dependencies for litellm (e.g., tiktoken)
            if "tiktoken" in str(e):
                raise ModuleNotFoundError(
                    "Missing required dependency 'tiktoken' for litellm. "
                    "Please reinstall aider with: pip install --upgrade --force-reinstall aider-chat"
                ) from e
            else:
                raise ModuleNotFoundError(
                    f"Failed to import litellm due to missing dependency: {e}. "
                    "Please reinstall aider with: pip install --upgrade --force-reinstall aider-chat"
                ) from e

        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()


litellm = LazyLiteLLM()

__all__ = [litellm]
