from pathlib import Path

from aider.llmapi import LLMApiModelManager
from aider.models import ModelInfoManager


class DummyResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, json_data):
        self.status_code = 200
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_llmapi_get_model_info_from_cache(monkeypatch, tmp_path):
    """
    LLMApiModelManager should return correct metadata taken from the
    downloaded (and locally cached) models JSON payload.
    """
    payload = {
        "data": [
            {
                "id": "gpt-4o",
                "context_window": 128000,
            },
            {
                "id": "claude-3-5-sonnet",
                "context_window": 200000,
            },
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = LLMApiModelManager()
    info = manager.get_model_info("llmapi/gpt-4o")

    assert info["max_input_tokens"] == 128000
    assert info["max_tokens"] == 128000
    assert info["litellm_provider"] == "openai"


def test_llmapi_get_available_models(monkeypatch, tmp_path):
    """
    LLMApiModelManager.get_available_models should return prefixed model names.
    """
    payload = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "claude-3-5-sonnet"},
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = LLMApiModelManager()
    models = manager.get_available_models()

    assert "llmapi/gpt-4o" in models
    assert "llmapi/claude-3-5-sonnet" in models


def test_llmapi_unknown_model_returns_empty(monkeypatch, tmp_path):
    """
    LLMApiModelManager should return an empty dict for unknown models.
    """
    payload = {"data": [{"id": "gpt-4o", "context_window": 128000}]}

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = LLMApiModelManager()
    info = manager.get_model_info("llmapi/does-not-exist")

    assert info == {}


def test_model_info_manager_uses_llmapi_manager(monkeypatch):
    """
    ModelInfoManager should delegate to LLMApiModelManager when litellm
    provides no data for a llmapi-prefixed model.
    """
    monkeypatch.setattr("aider.models.litellm.get_model_info", lambda *a, **k: {})

    stub_info = {
        "max_input_tokens": 128000,
        "max_tokens": 128000,
        "max_output_tokens": 128000,
        "litellm_provider": "openai",
    }

    monkeypatch.setattr(
        "aider.models.LLMApiModelManager.get_model_info",
        lambda self, model: stub_info,
    )

    mim = ModelInfoManager()
    info = mim.get_model_info("llmapi/gpt-4o")

    assert info == stub_info
