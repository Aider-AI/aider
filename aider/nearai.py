"""
NEAR AI Cloud model metadata caching and lookup.

This module keeps a local cached copy of the public NEAR AI Cloud model list
and exposes metadata in a format compatible with LiteLLM's get_model_info().
"""

import json
import time
from pathlib import Path

import requests


def _cost_per_token(cost):
    if not cost:
        return None
    try:
        amount = cost.get("amount")
        scale = cost.get("scale", 9)
        if amount is None:
            return None
        return amount * (10**-scale)
    except Exception:  # noqa: BLE001
        return None


def _model_mode(record):
    model_id = record.get("modelId", "")
    metadata = record.get("metadata") or {}
    architecture = metadata.get("architecture") or {}
    input_modalities = architecture.get("inputModalities") or []
    output_modalities = architecture.get("outputModalities") or []

    if "embedding" in output_modalities:
        return "embedding"
    if "image" in output_modalities:
        return "image_generation"
    if "audio" in input_modalities:
        return "audio_transcription"
    if "Reranker" in model_id or "score" in output_modalities:
        return "rerank"
    if "text" in output_modalities:
        return "chat"
    return None


class NearAIModelManager:
    MODELS_URL = "https://cloud-api.near.ai/v1/model/list"
    CACHE_TTL = 60 * 60 * 24  # 24 h

    def __init__(self):
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "nearai_models.json"
        self.content = None
        self.verify_ssl = True
        self._cache_loaded = False
        self._model_infos = None

    def set_verify_ssl(self, verify_ssl):
        self.verify_ssl = verify_ssl

    def get_model_info(self, model):
        return self.get_model_infos().get(self._normalize_model_name(model), {})

    def get_model_infos(self):
        self._ensure_content()
        if self._model_infos is not None:
            return self._model_infos

        infos = {}
        if not self.content or "models" not in self.content:
            self._model_infos = infos
            return infos

        for record in self.content["models"]:
            info = self._record_to_model_info(record)
            if not info:
                continue

            names = self._record_model_names(record)
            for name in names:
                infos[name] = info

        self._model_infos = infos
        return infos

    def _record_to_model_info(self, record):
        model_id = record.get("modelId")
        if not model_id or model_id == "openai/privacy-filter":
            return {}

        mode = _model_mode(record)
        if not mode:
            return {}

        metadata = record.get("metadata") or {}
        context_len = metadata.get("contextLength")
        info = {
            "max_input_tokens": context_len,
            "max_tokens": context_len,
            "max_output_tokens": context_len,
            "input_cost_per_token": _cost_per_token(record.get("inputCostPerToken")),
            "output_cost_per_token": _cost_per_token(record.get("outputCostPerToken")),
            "litellm_provider": "nearai",
            "mode": mode,
        }

        architecture = metadata.get("architecture") or {}
        input_modalities = architecture.get("inputModalities") or []
        if "image" in input_modalities:
            info["supports_vision"] = True
        if mode == "chat":
            info["supports_function_calling"] = True

        return info

    def _record_model_names(self, record):
        metadata = record.get("metadata") or {}
        names = [record.get("modelId")]
        names.extend(metadata.get("aliases") or [])
        return {
            self._normalize_model_name(name)
            for name in names
            if name and name != "openai/privacy-filter"
        }

    def _normalize_model_name(self, model):
        if model.startswith("nearai/"):
            return model
        return "nearai/" + model

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
            response = requests.get(self.MODELS_URL, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                self.content = response.json()
                self._model_infos = None
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=2))
                except OSError:
                    pass
        except Exception as ex:  # noqa: BLE001
            print(f"Failed to fetch NEAR AI Cloud model list: {ex}")
            try:
                self.cache_file.write_text("{}")
            except OSError:
                pass
