from pathlib import Path

from aider.models import Model, ModelInfoManager
from aider.nearai import NearAIModelManager
from aider.onboarding import try_to_select_default_model


class DummyResponse:
    def __init__(self, json_data):
        self.status_code = 200
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_nearai_get_model_info_from_cache(monkeypatch, tmp_path):
    payload = {
        "models": [
            {
                "modelId": "zai-org/GLM-5.1-FP8",
                "inputCostPerToken": {"amount": 1000, "scale": 9, "currency": "USD"},
                "outputCostPerToken": {"amount": 3000, "scale": 9, "currency": "USD"},
                "metadata": {
                    "contextLength": 202752,
                    "aliases": ["glm-latest"],
                    "architecture": {
                        "inputModalities": ["text"],
                        "outputModalities": ["text"],
                    },
                },
            },
            {
                "modelId": "openai/privacy-filter",
                "inputCostPerToken": {"amount": 0, "scale": 9, "currency": "USD"},
                "outputCostPerToken": {"amount": 0, "scale": 9, "currency": "USD"},
                "metadata": {
                    "contextLength": 512,
                    "architecture": {
                        "inputModalities": ["text"],
                        "outputModalities": ["text"],
                    },
                },
            },
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = NearAIModelManager()
    info = manager.get_model_info("nearai/zai-org/GLM-5.1-FP8")
    alias_info = manager.get_model_info("nearai/glm-latest")

    assert info["max_input_tokens"] == 202752
    assert abs(info["input_cost_per_token"] - 0.000001) < 0.000000000001
    assert abs(info["output_cost_per_token"] - 0.000003) < 0.000000000001
    assert info["litellm_provider"] == "nearai"
    assert info["mode"] == "chat"
    assert alias_info == info
    assert manager.get_model_info("nearai/openai/privacy-filter") == {}


def test_model_info_manager_uses_nearai_manager(monkeypatch):
    stub_info = {
        "max_input_tokens": 128000,
        "max_tokens": 128000,
        "max_output_tokens": 128000,
        "input_cost_per_token": 0.000001,
        "output_cost_per_token": 0.000003,
        "litellm_provider": "nearai",
        "mode": "chat",
    }

    def fail_litellm_lookup(*args, **kwargs):
        raise AssertionError("nearai should not require LiteLLM model metadata")

    monkeypatch.setattr("aider.models.litellm.get_model_info", fail_litellm_lookup)
    monkeypatch.setattr(
        "aider.models.NearAIModelManager.get_model_info",
        lambda self, model: stub_info,
    )

    manager = ModelInfoManager()
    info = manager.get_model_info("nearai/zai-org/GLM-5.1-FP8")

    assert info == stub_info


def test_nearai_completion_uses_openai_compatible_endpoint(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return "response"

    monkeypatch.setenv("NEARAI_API_KEY", "near-key")
    monkeypatch.setattr(
        "aider.models.Model.get_model_info",
        lambda self, model: {"max_input_tokens": 128000, "litellm_provider": "nearai"},
    )
    monkeypatch.setattr("aider.models.litellm.completion", fake_completion)

    model = Model("nearai/zai-org/GLM-5.1-FP8")
    model.extra_params = {
        "max_completion_tokens": 123,
        "store": True,
        "extra_body": {"reasoning_effort": "low", "foo": "bar"},
    }
    _hash, response = model.send_completion(
        [{"role": "developer", "content": "Use system-compatible role."}],
        functions=None,
        stream=False,
    )

    assert response == "response"
    assert captured["model"] == "openai/zai-org/GLM-5.1-FP8"
    assert captured["api_base"] == "https://cloud-api.near.ai/v1"
    assert captured["api_key"] == "near-key"
    assert captured["max_tokens"] == 123
    assert "max_completion_tokens" not in captured
    assert "store" not in captured
    assert captured["extra_body"] == {"foo": "bar"}
    assert captured["messages"][0]["role"] == "system"


def test_nearai_default_model_selection(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("NEARAI_API_KEY", "near-key")

    assert try_to_select_default_model() == "nearai/zai-org/GLM-5.1-FP8"


def test_nearai_alias_uses_default_model_settings(monkeypatch):
    monkeypatch.setenv("NEARAI_API_KEY", "near-key")
    monkeypatch.setattr(
        "aider.models.Model.get_model_info",
        lambda self, model: {"max_input_tokens": 128000, "litellm_provider": "nearai"},
    )

    model = Model("nearai")

    assert model.name == "nearai/zai-org/GLM-5.1-FP8"
    assert model.edit_format == "diff"
    assert model.use_repo_map


def test_nearai_does_not_advertise_unsupported_reasoning_settings(monkeypatch):
    monkeypatch.setenv("NEARAI_API_KEY", "near-key")
    monkeypatch.setattr(
        "aider.models.Model.get_model_info",
        lambda self, model: {"max_input_tokens": 128000, "litellm_provider": "nearai"},
    )

    model = Model("nearai/anthropic/claude-sonnet-4-6")

    assert "thinking_tokens" not in model.accepts_settings
    assert "reasoning_effort" not in model.accepts_settings
