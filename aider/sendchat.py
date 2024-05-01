import hashlib
import json

import backoff
import httpx
import litellm
import openai

# from diskcache import Cache
from openai import APIConnectionError, InternalServerError, RateLimitError

from aider.dump import dump  # noqa: F401

CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None
# CACHE = Cache(CACHE_PATH)

litellm.suppress_debug_info = True


@backoff.on_exception(
    backoff.expo,
    (
        InternalServerError,
        RateLimitError,
        APIConnectionError,
        httpx.ConnectError,
        litellm.exceptions.ServiceUnavailableError,
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

    key = json.dumps(kwargs, sort_keys=True).encode()

    # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    # del kwargs['stream']

    res = litellm.completion(**kwargs)

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
    except (AttributeError, openai.BadRequestError):
        return
