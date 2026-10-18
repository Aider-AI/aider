"""Ace Data Cloud's named transport for coding models."""

import os

MODEL_PREFIX = "acedatacloud/"
API_BASE = "https://api.acedata.cloud/v1"
API_KEY_ENV = "ACEDATACLOUD_API_KEY"


def is_model(name):
    return name.startswith(MODEL_PREFIX)


def transport_model(name):
    if not is_model(name):
        return name
    model = name[len(MODEL_PREFIX) :]
    if not model or not model.strip():
        raise ValueError("Select an Ace Data Cloud model: acedatacloud/<model>")
    return "openai/" + model


def validate_environment():
    present = bool(os.environ.get(API_KEY_ENV, "").strip())
    return dict(keys_in_environment=present, missing_keys=[] if present else [API_KEY_ENV])


def completion_kwargs(name):
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise ValueError(f"Ace Data Cloud requires {API_KEY_ENV}")
    return dict(
        model=transport_model(name),
        custom_llm_provider="openai",
        api_base=API_BASE,
        api_key=api_key,
    )
