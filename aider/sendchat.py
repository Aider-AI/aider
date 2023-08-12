import hashlib
import json
import logging

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

# Set up logging
logging.basicConfig(filename='chat.log', level=logging.INFO)
logger = logging.getLogger()

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

    key = json.dumps(kwargs, sort_keys=True).encode()

    # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    # Log the input arguments
    logger.info(f"Input arguments: {kwargs}")

    res = openai.ChatCompletion.create(**kwargs)

    # Log the response
    if res.choices and res.choices[0].message.content:
        logger.info(f"Response: {res.choices[0].message.content}")
    else:
        logger.error(f"Error: {res}")

    if not stream and CACHE is not None:
        CACHE[key] = res

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
