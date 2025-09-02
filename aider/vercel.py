"""
Vercel AI Gateway model metadata caching and lookup.

This module keeps a local cached copy of the Vercel AI Gateway model list
and exposes a helper class that returns metadata for a given model in a format
compatible with litellm's ``get_model_info``.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

import requests


def _cost_per_token(val: str | None) -> float | None:
    """Convert a price string (USD per token) to a float."""
    if val in (None, "", "0"):
        return 0.0 if val == "0" else None
    try:
        return float(val)
    except Exception:  # noqa: BLE001
        return None


class VercelAIGatewayModelManager:
    MODELS_URL = "https://ai-gateway.vercel.sh/v1/models"
    CACHE_TTL = 60 * 60 * 24  # 24 h

    def __init__(self) -> None:
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "vercel_models.json"
        self.content: Dict | None = None
        self.verify_ssl: bool = True
        self._cache_loaded = False

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def set_verify_ssl(self, verify_ssl: bool) -> None:
        """Enable/disable SSL verification for API requests."""
        self.verify_ssl = verify_ssl

    def get_model_info(self, model: str) -> Dict:
        """
        Return metadata for *model* or an empty ``dict`` when unknown.

        ``model`` should use the aider naming convention, e.g.
        ``vercel_ai_gateway/openai/gpt-4`` or
        ``vercel_ai_gateway/anthropic/claude-3-5-sonnet-20241022``.
        """
        self._ensure_content()
        if not self.content or "data" not in self.content:
            return {}

        route = self._strip_prefix(model)

        # Only consider language models
        record = next(
            (
                item
                for item in self.content["data"]
                if item.get("id") == route and item.get("type") == "language"
            ),
            None,
        )
        if not record:
            return {}

        context_len = record.get("context_window") or None

        pricing = record.get("pricing", {})
        return {
            "max_input_tokens": context_len,
            "max_tokens": context_len,
            "max_output_tokens": context_len,
            "input_cost_per_token": _cost_per_token(pricing.get("input")),
            "output_cost_per_token": _cost_per_token(pricing.get("output")),
            "litellm_provider": "vercel_ai_gateway",
        }

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _strip_prefix(self, model: str) -> str:
        return (
            model[len("vercel_ai_gateway/") :] if model.startswith("vercel_ai_gateway/") else model
        )

    def _ensure_content(self) -> None:
        self._load_cache()
        if not self.content:
            self._update_cache()

    def _load_cache(self) -> None:
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
            # Cache directory might be unwritable; ignore.
            pass

        self._cache_loaded = True

    def _update_cache(self) -> None:
        try:
            response = requests.get(self.MODELS_URL, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=2))
                except OSError:
                    pass  # Non-fatal if we can't write the cache
        except Exception as ex:  # noqa: BLE001
            print(f"Failed to fetch Vercel AI Gateway model list: {ex}")
            try:
                self.cache_file.write_text("{}")
            except OSError:
                pass
