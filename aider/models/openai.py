from dataclasses import dataclass, fields

import tiktoken

from aider.dump import dump  # noqa: F401

from .model import Model


@dataclass
class ModelInfo:
    name: str
    max_context_tokens: int
    prompt_price: float
    completion_price: float
    edit_format: str
    always_available: bool = False
    use_repo_map: bool = False
    send_undo_reply: bool = False


# https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
# https://platform.openai.com/docs/models/gpt-3-5-turbo
# https://openai.com/pricing

openai_models = [
    # gpt-3.5
    ModelInfo(
        "gpt-3.5-turbo-0125",
        16385,
        0.0005,
        0.0015,
        "whole",
        always_available=True,
    ),
    ModelInfo(
        "gpt-3.5-turbo-1106",
        16385,
        0.0010,
        0.0020,
        "whole",
        always_available=True,
    ),
    ModelInfo(
        "gpt-3.5-turbo-0613",
        4096,
        0.0015,
        0.0020,
        "whole",
        always_available=True,
    ),
    ModelInfo(
        "gpt-3.5-turbo-16k-0613",
        16385,
        0.0030,
        0.0040,
        "whole",
        always_available=True,
    ),
    # gpt-4
    ModelInfo(
        "gpt-4-0125-preview",
        128000,
        0.01,
        0.03,
        "udiff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelInfo(
        "gpt-4-1106-preview",
        128000,
        0.01,
        0.03,
        "udiff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelInfo(
        "gpt-4-vision-preview",
        128000,
        0.01,
        0.03,
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelInfo(
        "gpt-4-0613",
        8192,
        0.03,
        0.06,
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelInfo(
        "gpt-4-32k-0613",
        32768,
        0.06,
        0.12,
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
]

openai_aliases = {
    # gpt-3.5
    "gpt-3.5-turbo": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    # gpt-4
    "gpt-4-turbo-preview": "gpt-4-0125-preview",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
}


class OpenAIModel(Model):
    def __init__(self, name):
        true_name = openai_aliases.get(name, name)

        try:
            self.tokenizer = tiktoken.encoding_for_model(true_name)
        except KeyError:
            raise ValueError(f"No known tokenizer for model: {name}")

        model_info = self.lookup_model_info(true_name)
        if not model_info:
            raise ValueError(f"Unsupported model: {name}")

        for field in fields(ModelInfo):
            val = getattr(model_info, field.name)
            setattr(self, field.name, val)

        # restore the caller's specified name
        self.name = name

        # set the history token limit
        if self.max_context_tokens < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024

    def lookup_model_info(self, name):
        for mi in openai_models:
            if mi.name == name:
                return mi
