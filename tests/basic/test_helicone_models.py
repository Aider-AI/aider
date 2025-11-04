import os
from unittest.mock import patch

from aider.models import Model


def test_helicone_missing_key():
    with patch.dict(os.environ, {}, clear=True):
        m = Model("helicone/openai/gpt-4o")
        assert m.missing_keys and "HELICONE_API_KEY" in m.missing_keys
        assert m.keys_in_environment is False


def test_helicone_with_key():
    with patch.dict(os.environ, {"HELICONE_API_KEY": "test"}, clear=True):
        m = Model("helicone/gpt-4o")
        assert m.missing_keys == []
        assert m.keys_in_environment == ["HELICONE_API_KEY"]
