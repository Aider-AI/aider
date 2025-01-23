import hashlib
import json
import os
import time

from aider.dump import dump  # noqa: F401
from aider.exceptions import LiteLLMExceptions
from aider.llm import litellm
from aider.utils import format_messages

RETRY_TIMEOUT = 60


def sanity_check_messages(messages):
    """Check if messages alternate between user and assistant roles.
    System messages can be interspersed anywhere.
    Also verifies the last non-system message is from the user.
    Returns True if valid, False otherwise."""
    last_role = None
    last_non_system_role = None

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue

        if last_role and role == last_role:
            turns = format_messages(messages)
            raise ValueError("Messages don't properly alternate user/assistant:\n\n" + turns)

        last_role = role
        last_non_system_role = role

    # Ensure last non-system message is from user
    return last_non_system_role == "user"



def simple_send_with_retries(model, messages):
    litellm_ex = LiteLLMExceptions()

    retry_delay = 0.125
    while True:
        try:
            kwargs = {
                "model_name": model.name,
                "messages": messages,
                "functions": None,
                "stream": False,
                "temperature": None if not model.use_temperature else 0,
                "extra_params": model.extra_params,
            }

            _hash, response = model.send_completion(**kwargs)
            if not response or not hasattr(response, "choices") or not response.choices:
                return None
            return response.choices[0].message.content
        except litellm_ex.exceptions_tuple() as err:
            ex_info = litellm_ex.get_ex_info(err)

            print(str(err))
            if ex_info.description:
                print(ex_info.description)

            should_retry = ex_info.retry
            if should_retry:
                retry_delay *= 2
                if retry_delay > RETRY_TIMEOUT:
                    should_retry = False

            if not should_retry:
                return None

            print(f"Retrying in {retry_delay:.1f} seconds...")
            time.sleep(retry_delay)
            continue
        except AttributeError:
            return None
