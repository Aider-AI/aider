import importlib
import os
import sys
import threading
import warnings

from aider import urls, utils
from aider.dump import dump  # noqa: F401

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

AIDER_SITE_URL = "https://aider.chat"
AIDER_APP_NAME = "Aider"

os.environ["OR_SITE_URL"] = AIDER_SITE_URL
os.environ["OR_APP_NAME"] = AIDER_APP_NAME
os.environ["LITELLM_MODE"] = "PRODUCTION"

# `import litellm` takes 1.5 seconds, defer it!

VERBOSE = False


def _import_litellm():
    return importlib.import_module("litellm")


class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _recover_aiohttp(self):
        prompt_text = (
            "Missing Required Dependency\n\n"
            "The 'aiohttp' module is not installed.\n"
            "This module is required to run Aider with LiteLLM.\n\n"
            "Would you like to install it now?\n\n"
            "[Y] Yes — Install aiohttp\n"
            "[N] No — Exit Aider"
        )
        print(prompt_text)
        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"

        if not (choice.startswith("y") or choice == "yes"):
            sys.exit(1)

        cmd = utils.get_pip_install(["aiohttp"])
        success, _ = utils.run_install(cmd)

        if success:
            print("Loading aiohttp...")
            try:
                importlib.invalidate_caches()
                __import__("aiohttp")
                return True
            except ModuleNotFoundError:
                pass

        print("\nInstallation failed.", file=sys.stderr)
        print("Please install 'aiohttp' manually using:", file=sys.stderr)
        print(f"  {utils.printable_shell_command(cmd)}", file=sys.stderr)
        print(f"See {urls.install_properly} for more info.", file=sys.stderr)
        sys.exit(1)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return

        if VERBOSE:
            print("Loading litellm...")

        try:
            self._lazy_module = _import_litellm()
        except ModuleNotFoundError as err:
            if getattr(err, "name", None) == "aiohttp":
                if threading.current_thread() is not threading.main_thread():
                    raise

                self._recover_aiohttp()
                print("Loading litellm...")
                try:
                    self._lazy_module = _import_litellm()
                except ModuleNotFoundError as retry_err:
                    if getattr(retry_err, "name", None) in ("litellm", "aiohttp"):
                        print(f"Error: {retry_err}", file=sys.stderr)
                        print(
                            "Error loading required imports. Did you install aider properly?",
                            file=sys.stderr,
                        )
                        print(f"See {urls.install_properly} for more info.", file=sys.stderr)
                        sys.exit(1)
                    else:
                        raise
            elif getattr(err, "name", None) == "litellm":
                print(f"Error: {err}", file=sys.stderr)
                print(
                    "Error loading required imports. Did you install aider properly?",
                    file=sys.stderr,
                )
                print(f"See {urls.install_properly} for more info.", file=sys.stderr)
                sys.exit(1)
            else:
                raise

        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()


litellm = LazyLiteLLM()

__all__ = [litellm]
