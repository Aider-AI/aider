import importlib
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

os.environ["OR_SITE_URL"] = "http://aider.chat"
os.environ["OR_APP_NAME"] = "Aider"

# `import litellm` takes 1.5 seconds, defer it!


class LazyLiteLLM:
    def __init__(self):
        self._lazy_module = None

    def __getattr__(self, name):
        if self._lazy_module is None:
            self._lazy_module = importlib.import_module("litellm")

            self._lazy_module.suppress_debug_info = True
            self._lazy_module.set_verbose = False
            self._lazy_module.drop_params = True

        return getattr(self._lazy_module, name)


litellm = LazyLiteLLM()

__all__ = [litellm]
