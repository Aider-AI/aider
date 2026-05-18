from pathlib import Path

from aider.models import ModelInfoManager
from aider.orcarouter import OrcaRouterModelManager


class DummyResponse:
    """Minimal stand-in for requests.Response used in tests."""

    def __init__(self, json_data):
        self.status_code = 200
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_orcarouter_get_model_info_from_cache(monkeypatch, tmp_path):
    """
    OrcaRouterModelManager should return correct metadata derived from the
    /api/pricing payload using the model_ratio / completion_ratio formula.

    For model_ratio=1.25 and completion_ratio=4 (e.g. openai/gpt-4o):
      input  per token = 1.25 * 2 / 1_000_000 = 2.5e-6   ($2.50 / 1M)
      output per token = 1.25 * 4 * 2 / 1_000_000 = 1.0e-5 ($10.00 / 1M)
    """
    payload = [
        {
            "model_name": "openai/gpt-4o",
            "model_ratio": 1.25,
            "completion_ratio": 4,
            "context_length": 128000,
            "max_completion_tokens": 16384,
        }
    ]

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = OrcaRouterModelManager()
    info = manager.get_model_info("orcarouter/openai/gpt-4o")

    assert info["max_input_tokens"] == 128000
    assert info["max_output_tokens"] == 16384
    assert info["input_cost_per_token"] == 2.5e-6
    assert info["output_cost_per_token"] == 1.0e-5
    assert info["litellm_provider"] == "orcarouter"


def test_orcarouter_get_model_info_wrapped_payload(monkeypatch, tmp_path):
    """Accept the alternative {"data": [...]} wrapper shape."""
    payload = {
        "data": [
            {
                "model_name": "anthropic/claude-opus-4.7",
                "model_ratio": 2.5,
                "completion_ratio": 5,
                "context_length": 200000,
            }
        ]
    }

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(payload))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = OrcaRouterModelManager()
    info = manager.get_model_info("orcarouter/anthropic/claude-opus-4.7")

    assert info["max_input_tokens"] == 200000
    assert info["input_cost_per_token"] == 5.0e-6  # $5/M
    assert info["output_cost_per_token"] == 2.5e-5  # $25/M
    assert info["litellm_provider"] == "orcarouter"


def test_orcarouter_unknown_model_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse([]))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    manager = OrcaRouterModelManager()
    info = manager.get_model_info("orcarouter/unknown/model")

    assert info == {}


def test_model_info_manager_uses_orcarouter_manager(monkeypatch):
    """
    ModelInfoManager should delegate to OrcaRouterModelManager when litellm
    provides no data for an orcarouter/-prefixed model.
    """
    monkeypatch.setattr("aider.models.litellm.get_model_info", lambda *a, **k: {})

    stub_info = {
        "max_input_tokens": 1024,
        "max_tokens": 1024,
        "max_output_tokens": 1024,
        "input_cost_per_token": 1.0e-6,
        "output_cost_per_token": 2.0e-6,
        "litellm_provider": "orcarouter",
    }

    monkeypatch.setattr(
        "aider.models.OrcaRouterModelManager.get_model_info",
        lambda self, model: stub_info,
    )

    mim = ModelInfoManager()
    info = mim.get_model_info("orcarouter/fake/model")

    assert info == stub_info
