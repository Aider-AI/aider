import hashlib
import json

import backoff

from aider.dump import dump  # noqa: F401
from aider.llm import litellm

# from diskcache import Cache


CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None
# CACHE = Cache(CACHE_PATH)


def lazy_litellm_retry_decorator(func):
    def wrapper(*args, **kwargs):
        import httpx

        decorated_func = backoff.on_exception(
            backoff.expo,
            (
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.ReadTimeout,
                litellm.exceptions.APIConnectionError,
                litellm.exceptions.APIError,
                litellm.exceptions.RateLimitError,
                litellm.exceptions.ServiceUnavailableError,
                litellm.exceptions.Timeout,
                litellm.exceptions.InternalServerError,
                litellm.llms.anthropic.AnthropicError,
            ),
            max_time=60,
            on_backoff=lambda details: print(
                f"{details.get('exception', 'Exception')}\nRetry in {details['wait']:.1f} seconds."
            ),
        )(func)
        return decorated_func(*args, **kwargs)

    return wrapper


@lazy_litellm_retry_decorator
def send_with_retries(
    model_name, messages, functions, stream, temperature=0, extra_headers=None, max_tokens=None
):
    from aider.llm import litellm

    kwargs = dict(
        model=model_name,
        messages=messages,
        temperature=temperature,
        stream=stream,
    )
    if functions is not None:
        kwargs["functions"] = functions
    if extra_headers is not None:
        kwargs["extra_headers"] = extra_headers
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

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
    except (AttributeError, litellm.exceptions.BadRequestError):
        return
