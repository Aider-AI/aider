from pathlib import Path

from aider.eurouter import EURouterModelManager
from aider.models import ModelInfoManager


class DummyResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, json_data):
        self.status_code = 200
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_eurouter_get_model_info_from_cache(monkeypatch, tmp_path):
    """
    EURouterModelManager should return correct metadata taken from the
    downloaded (and locally cached) models JSON payload.
    """
    payload = {
        "data": [
            {
                "id": "claude-opus-4-6",
                "context_length": 200000,
                "pricing": {"prompt": "0.000015", "completion": "0.000075"},
                "top_provider": {"context_length": 200000},
            }
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = EURouterModelManager()
    info = manager.get_model_info("eurouter/claude-opus-4-6")

    assert info["max_input_tokens"] == 200000
    assert info["input_cost_per_token"] == 0.000015
    assert info["output_cost_per_token"] == 0.000075
    assert info["litellm_provider"] == "eurouter"


def test_eurouter_model_with_variant(monkeypatch, tmp_path):
    """
    EURouterModelManager should handle :variant suffixes correctly,
    falling back to the base model ID.
    """
    payload = {
        "data": [
            {
                "id": "claude-opus-4-6",
                "context_length": 200000,
                "pricing": {"prompt": "0.000015", "completion": "0.000075"},
                "top_provider": {"context_length": 200000},
            }
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = EURouterModelManager()
    info = manager.get_model_info("eurouter/claude-opus-4-6:floor")

    assert info["max_input_tokens"] == 200000
    assert info["litellm_provider"] == "eurouter"


def test_model_info_manager_uses_eurouter_manager(monkeypatch):
    """
    ModelInfoManager should delegate to EURouterModelManager when litellm
    provides no data for a eurouter/-prefixed model.
    """
    monkeypatch.setattr("aider.models.litellm.get_model_info", lambda *a, **k: {})

    stub_info = {
        "max_input_tokens": 200000,
        "max_tokens": 200000,
        "max_output_tokens": 200000,
        "input_cost_per_token": 0.000015,
        "output_cost_per_token": 0.000075,
        "litellm_provider": "eurouter",
    }

    monkeypatch.setattr(
        "aider.models.EURouterModelManager.get_model_info",
        lambda self, model: stub_info,
    )

    mim = ModelInfoManager()
    info = mim.get_model_info("eurouter/claude-opus-4-6")

    assert info == stub_info
