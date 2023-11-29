import hashlib
import json

import backoff
import openai
import requests

# from diskcache import Cache
from openai.error import (
    APIConnectionError,
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None
# CACHE = Cache(CACHE_PATH)


@backoff.on_exception(
    backoff.expo,
    (
        Timeout,
        APIError,
        ServiceUnavailableError,
        RateLimitError,
        APIConnectionError,
        requests.exceptions.ConnectionError,
    ),
    max_tries=10,
    on_backoff=lambda details: print(
        f"{details.get('exception','Exception')}\nRetry in {details['wait']:.1f} seconds."
    ),
)
def send_with_retries(model_name, messages, functions, stream):
    kwargs = dict(
        model=model_name,
        messages=messages,
        temperature=0,
        stream=stream,
    )
    if functions is not None:
        kwargs["functions"] = functions

    # we are abusing the openai object to stash these values
    if hasattr(openai, "api_deployment_id"):
        kwargs["deployment_id"] = openai.api_deployment_id
    if hasattr(openai, "api_engine"):
        kwargs["engine"] = openai.api_engine

    if "openrouter.ai" in openai.api_base:
        kwargs["headers"] = {"HTTP-Referer": "http://aider.chat", "X-Title": "Aider"}

    # Check conditions to switch to gpt-4-vision-preview
    if "openrouter.ai" not in openai.api_base and model_name.startswith("gpt-4"):
        if any(isinstance(msg.get("content"), list) and any("image_url" in item for item in msg.get("content") if isinstance(item, dict)) for msg in messages):
            kwargs['model'] = "gpt-4-vision-preview"
            # looks like gpt-4-vision is limited to max tokens of 4096
            kwargs["max_tokens"] = 4096

    key = json.dumps(kwargs, sort_keys=True).encode()

    # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    res = openai.ChatCompletion.create(**kwargs)

    if not stream and CACHE is not None:
        CACHE[key] = res

    return hash_object, res


def simple_send_with_retries(model_name, messages):
    try:
        _hash, response = send_with_retries(
            model_name=model_name,
            messages=messages,
            functions=None,
            stream=False,
        )
        return response.choices[0].message.content
    except (AttributeError, openai.error.InvalidRequestError):
        return
