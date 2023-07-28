import hashlib
import json

import backoff
import openai
import requests
from openai.error import (
    APIConnectionError,
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)


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
def send_with_retries(model, messages, functions, stream):
    kwargs = dict(
        model=model,
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

    # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
    hash_object = hashlib.sha1(json.dumps(kwargs, sort_keys=True).encode())

    res = openai.ChatCompletion.create(**kwargs)
    return hash_object, res


def simple_send_with_retries(model, messages):
    try:
        _hash, response = send_with_retries(
            model=model,
            messages=messages,
            functions=None,
            stream=False,
        )
        return response.choices[0].message.content
    except (AttributeError, openai.error.InvalidRequestError):
        return
