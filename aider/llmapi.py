"""
LLM API model metadata caching and lookup.

This module keeps a local cached copy of the LLM API model list
(downloaded from ``https://api.llmapi.ai/v1/models``) and exposes a
helper class that returns metadata for a given model in a format compatible
with litellm's ``get_model_info``.

Authorization is NOT required for the models endpoint.
"""
import json
import time
from pathlib import Path


class LLMApiModelManager:
    MODELS_URL = "https://api.llmapi.ai/v1/models"
    CACHE_TTL = 60 * 60 * 24  # 24 h
    PREFIX = "llmapi/"

    def __init__(self):
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "llmapi_models.json"
        self.content = None
        self.verify_ssl = True
        self._cache_loaded = False

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def set_verify_ssl(self, verify_ssl):
        """Enable/disable SSL verification for API requests."""
        self.verify_ssl = verify_ssl

    def get_model_info(self, model):
        """
        Return metadata for *model* or an empty ``dict`` when unknown.

        ``model`` should use the aider naming convention, e.g.
        ``llmapi/gpt-4o``.
        """
        self._ensure_content()
        if not self.content or "data" not in self.content:
            return {}

        model_id = self._strip_prefix(model)

        record = next(
            (item for item in self.content["data"] if item.get("id") == model_id),
            None,
        )
        if not record:
            return {}

        context_len = record.get("context_window") or record.get("context_length") or None

        return {
            "max_input_tokens": context_len,
            "max_tokens": context_len,
            "max_output_tokens": context_len,
            "litellm_provider": "openai",
        }

    def get_available_models(self):
        """Return a list of ``llmapi/<id>`` model names available on the API."""
        self._ensure_content()
        if not self.content or "data" not in self.content:
            return []
        return [self.PREFIX + item["id"] for item in self.content["data"] if item.get("id")]

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    def _strip_prefix(self, model):
        return model[len(self.PREFIX) :] if model.startswith(self.PREFIX) else model

    def _ensure_content(self):
        self._load_cache()
        if not self.content:
            self._update_cache()

    def _load_cache(self):
        if self._cache_loaded:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if self.cache_file.exists():
                cache_age = time.time() - self.cache_file.stat().st_mtime
                if cache_age < self.CACHE_TTL:
                    try:
                        self.content = json.loads(self.cache_file.read_text())
                    except json.JSONDecodeError:
                        self.content = None
        except OSError:
            pass

        self._cache_loaded = True

    def _update_cache(self):
        try:
            import requests

            response = requests.get(self.MODELS_URL, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=2))
                except OSError:
                    pass
        except Exception as ex:  # noqa: BLE001
            print(f"Failed to fetch LLM API model list: {ex}")
            try:
                self.cache_file.write_text("{}")
            except OSError:
                pass
