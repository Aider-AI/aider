"""
OrcaRouter model metadata caching and lookup.

OrcaRouter (https://www.orcarouter.ai) is an OpenAI-compatible LLM meta-router
that exposes 150+ upstream models under the ``orcarouter/<vendor>/<model>``
naming convention plus a virtual ``orcarouter/auto`` adaptive router.

This module keeps a local cached copy of the OrcaRouter pricing/catalog feed
(downloaded from ``https://www.orcarouter.ai/api/pricing`` -- a public endpoint
that needs no auth) and exposes a helper class that returns metadata for a
given model in a format compatible with litellm's ``get_model_info``.

Pricing formula (per OrcaRouter quota constant ``QuotaPerUnit = 500_000``,
i.e. $2 per 1M tokens for ``model_ratio = 1``):

    input  USD/token = model_ratio * 2 / 1_000_000
    output USD/token = model_ratio * completion_ratio * 2 / 1_000_000
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

import requests


# $2 / 1M tokens per unit ratio. Source: OrcaRouter common/constants.go QuotaPerUnit.
_USD_PER_M_TOKENS_AT_RATIO_1 = 2.0


def _per_token(usd_per_million):
    """Convert USD-per-1M-tokens to USD-per-token, or None on bad input."""
    if usd_per_million is None:
        return None
    try:
        return float(usd_per_million) / 1_000_000.0
    except (TypeError, ValueError):
        return None


class OrcaRouterModelManager:
    MODELS_URL = "https://www.orcarouter.ai/api/pricing"
    CACHE_TTL = 60 * 60 * 24  # 24 h

    def __init__(self):
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "orcarouter_models.json"
        self.content = None
        self.verify_ssl = True
        self._cache_loaded = False

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def set_verify_ssl(self, verify_ssl):
        """Enable/disable SSL verification for API requests."""
        self.verify_ssl = verify_ssl

    def get_model_info(self, model):
        """
        Return metadata for *model* or an empty ``dict`` when unknown.

        ``model`` should use the aider naming convention, e.g.
        ``orcarouter/openai/gpt-4o`` or ``orcarouter/anthropic/claude-opus-4.7``.
        """
        self._ensure_content()
        records = self._records()
        if not records:
            return {}

        route = self._strip_prefix(model)
        record = next(
            (item for item in records if item.get("model_name") == route),
            None,
        )
        if not record:
            return {}

        try:
            model_ratio = float(record.get("model_ratio") or 0)
        except (TypeError, ValueError):
            model_ratio = 0.0
        try:
            completion_ratio = float(record.get("completion_ratio") or 1)
        except (TypeError, ValueError):
            completion_ratio = 1.0

        input_per_m = model_ratio * _USD_PER_M_TOKENS_AT_RATIO_1
        output_per_m = model_ratio * completion_ratio * _USD_PER_M_TOKENS_AT_RATIO_1

        context_length = record.get("context_length") or None
        max_output = record.get("max_completion_tokens") or context_length

        return {
            "max_input_tokens": context_length,
            "max_tokens": context_length,
            "max_output_tokens": max_output,
            "input_cost_per_token": _per_token(input_per_m),
            "output_cost_per_token": _per_token(output_per_m),
            "litellm_provider": "orcarouter",
        }

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    def _strip_prefix(self, model):
        return model[len("orcarouter/"):] if model.startswith("orcarouter/") else model

    def _records(self):
        """Return list of model records regardless of whether the API wraps them."""
        if isinstance(self.content, list):
            return self.content
        if isinstance(self.content, dict):
            for key in ("data", "models", "pricing"):
                val = self.content.get(key)
                if isinstance(val, list):
                    return val
        return []

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
            response = requests.get(
                self.MODELS_URL, timeout=10, verify=self.verify_ssl
            )
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=2))
                except OSError:
                    pass
        except Exception as ex:  # noqa: BLE001
            print(f"Failed to fetch OrcaRouter model list: {ex}")
            try:
                self.cache_file.write_text("{}")
            except OSError:
                pass
