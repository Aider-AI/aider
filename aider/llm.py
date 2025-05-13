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

        self._lazy_module = importlib.import_module("litellm")

        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()

        # Configure Langfuse if environment variables are set
        langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        langfuse_host = os.getenv("LANGFUSE_HOST")

        if langfuse_public_key and langfuse_secret_key and langfuse_host:
            self._lazy_module.success_callback = ["langfuse"]
            self._lazy_module.failure_callback = ["langfuse"]
            if VERBOSE:
                print(f"Langfuse integration enabled, host: {langfuse_host}")
        elif VERBOSE and (langfuse_public_key or langfuse_secret_key or langfuse_host):
            # This case helps debug if only some variables are set
            print("Langfuse integration not fully configured; ensure LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST are all set.")


litellm = LazyLiteLLM()

__all__ = [litellm]
