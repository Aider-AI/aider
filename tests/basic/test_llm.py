import importlib
import os
from unittest.mock import patch

import aider.llm


def _reload_llm(env):
    # Keep the shared lazy litellm instance that other modules already imported
    lazy_litellm = aider.llm.litellm
    try:
        with patch.dict(os.environ, env, clear=True):
            importlib.reload(aider.llm)
            return os.environ.get("OR_SITE_URL"), os.environ.get("OR_APP_NAME")
    finally:
        aider.llm.litellm = lazy_litellm


def test_openrouter_attribution_defaults_applied_when_unset():
    site, app = _reload_llm({})
    assert site == aider.llm.AIDER_SITE_URL
    assert app == aider.llm.AIDER_APP_NAME


def test_openrouter_attribution_respects_preset_env():
    site, app = _reload_llm({"OR_SITE_URL": "https://example.com", "OR_APP_NAME": "Example"})
    assert site == "https://example.com"
    assert app == "Example"
