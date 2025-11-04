"""
Helicone model registry caching and lookup.

This module keeps a local cached copy of the Helicone public model registry
and exposes a helper class that returns metadata for a given model in a format
compatible with litellm’s get_model_info expectations.

Helicone models are addressed in aider as:
    helicone/<registry-id>

Where <registry-id> typically looks like "openai/gpt-4o" or similar. This
module is conservative about costs (sets None when unknown) and focuses on
returning context limits and provider mapping.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests


class HeliconeModelManager:
    DEFAULT_ENDPOINT = "https://jawn.helicone.ai/v1/public/model-registry/models"
    CACHE_TTL = 60 * 60 * 24  # 24 h

    def __init__(self) -> None:
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "helicone_models.json"
        self.content: Dict | None = None
        self.verify_ssl: bool = True
        self._cache_loaded = False

    def set_verify_ssl(self, verify_ssl: bool) -> None:
        self.verify_ssl = verify_ssl

    # Public API ---------------------------------------------------------
    def get_model_info(self, model: str) -> Dict:
        """
        Return metadata for a model named like 'helicone/<registry-id>'.
        Returns an empty dict for unknown models or on fetch failures.
        """
        if not model.startswith("helicone/"):
            return {}

        self._ensure_content()
        data = self._get_models_array()
        if not data:
            return {}

        route = model[len("helicone/") :]

        # Consider both the exact id and id without any ":suffix".
        candidates = {route}
        if ":" in route:
            candidates.add(route.split(":", 1)[0])

        record = next((m for m in data if m.get("id") in candidates), None)
        if not record:
            return {}

        # Prefer endpoint provider if available, otherwise try to infer from id prefix
        provider = None
        endpoints = record.get("endpoints") or []
        if endpoints:
            endpoint0 = endpoints[0] or {}
            provider = endpoint0.get("provider") or endpoint0.get("providerSlug")
        if not provider:
            # Infer provider from id like "openai/gpt-4o"
            if "/" in record.get("id", ""):
                provider = record["id"].split("/", 1)[0]

        context_len = record.get("contextLength") or record.get("maxOutput") or None

        # Helicone pricing schema may vary; set costs conservatively to None when unknown
        pricing = (endpoints[0] or {}).get("pricing") if endpoints else None
        input_cost = None
        output_cost = None
        if isinstance(pricing, dict):
            # Some registries store per-token USD as float; otherwise leave None
            try:
                p = pricing.get("prompt")
                input_cost = float(p) if p is not None else None
            except Exception:
                input_cost = None
            try:
                c = pricing.get("completion")
                output_cost = float(c) if c is not None else None
            except Exception:
                output_cost = None

        return {
            "max_input_tokens": context_len,
            "max_tokens": context_len,
            "max_output_tokens": context_len,
            "input_cost_per_token": input_cost,
            "output_cost_per_token": output_cost,
            # litellm_provider should be the underlying provider; consumers
            # can still rewrite the name if routing via Helicone.
            "litellm_provider": (provider or ""),
        }

    def get_all_model_ids(self) -> List[str]:
        """Return a list of all registry ids (without the 'helicone/' prefix)."""
        self._ensure_content()
        data = self._get_models_array()
        if not data:
            return []
        out: List[str] = []
        for m in data:
            mid = m.get("id")
            if isinstance(mid, str) and mid:
                out.append(mid)
        return out

    # Internal helpers ---------------------------------------------------
    def _get_models_array(self) -> Optional[List[Dict]]:
        if not self.content:
            return None
        obj = self.content.get("data") or {}
        arr = obj.get("models")
        if isinstance(arr, list):
            return arr
        return None

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
            response = requests.get(self.DEFAULT_ENDPOINT, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=2))
                except OSError:
                    pass
        except Exception as ex:  # noqa: BLE001
            print(f"Failed to fetch Helicone model registry: {ex}")
            try:
                self.cache_file.write_text("{}")
            except OSError:
                pass
