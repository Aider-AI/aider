from pathlib import Path

from aider.models import ModelInfoManager
from aider.openrouter import OpenRouterModelManager


class DummyResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, json_data):
        self.status_code = 200
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_openrouter_get_model_info_from_cache(monkeypatch, tmp_path):
    """
    OpenRouterModelManager should return correct metadata taken from the
    downloaded (and locally cached) models JSON payload.
    """
    payload = {
        "data": [
            {
                "id": "mistralai/mistral-medium-3",
                "context_length": 32768,
                "pricing": {"prompt": "100", "completion": "200"},
                "top_provider": {"context_length": 32768},
            }
        ]
    }

    # Fake out the network call and the HOME directory used for the cache file
    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = OpenRouterModelManager()
    info = manager.get_model_info("openrouter/mistralai/mistral-medium-3")

    assert info["max_input_tokens"] == 32768
    assert info["input_cost_per_token"] == 100.0
    assert info["output_cost_per_token"] == 200.0
    assert info["litellm_provider"] == "openrouter"


def test_model_info_manager_uses_openrouter_manager(monkeypatch):
    """
    ModelInfoManager should delegate to OpenRouterModelManager when litellm
    provides no data for an OpenRouter-prefixed model.
    """
    # Ensure litellm path returns no info so that fallback logic triggers
    monkeypatch.setattr("aider.models.litellm.get_model_info", lambda *a, **k: {})

    stub_info = {
        "max_input_tokens": 512,
        "max_tokens": 512,
        "max_output_tokens": 512,
        "input_cost_per_token": 100.0,
        "output_cost_per_token": 200.0,
        "litellm_provider": "openrouter",
    }

    # Force OpenRouterModelManager to return our stub info
    monkeypatch.setattr(
        "aider.models.OpenRouterModelManager.get_model_info",
        lambda self, model: stub_info,
    )

    mim = ModelInfoManager()
    info = mim.get_model_info("openrouter/fake/model")

    assert info == stub_info
