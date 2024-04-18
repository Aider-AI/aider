import json
import math
from dataclasses import dataclass, fields
from typing import Optional

import litellm
from PIL import Image

from aider.dump import dump  # noqa: F401

DEFAULT_MODEL_NAME = "gpt-4-1106-preview"


class NoModelInfo(Exception):
    """
    Exception raised when model information cannot be retrieved.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "No model information available.")


@dataclass
class ModelSettings:
    name: str
    edit_format: str
    weak_model_name: str = "gpt-3.5-turbo-0125"
    use_repo_map: bool = False
    send_undo_reply: bool = False


# https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
# https://platform.openai.com/docs/models/gpt-3-5-turbo
# https://openai.com/pricing

MODEL_SETTINGS = [
    # gpt-3.5
    ModelSettings(
        "gpt-3.5-turbo-0125",
        "whole",
    ),
    ModelSettings(
        "gpt-3.5-turbo-1106",
        "whole",
    ),
    ModelSettings(
        "gpt-3.5-turbo-0613",
        "whole",
    ),
    ModelSettings(
        "gpt-3.5-turbo-16k-0613",
        "whole",
    ),
    # gpt-4
    ModelSettings(
        "gpt-4-turbo-2024-04-09",
        "udiff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gpt-4-0125-preview",
        "udiff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gpt-4-1106-preview",
        "udiff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gpt-4-vision-preview",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gpt-4-0613",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gpt-4-32k-0613",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    # Claude
    ModelSettings(
        "claude-3-opus-20240229",
        "udiff",
        weak_model_name="claude-3-haiku-20240307",
        use_repo_map=True,
        send_undo_reply=True,
    ),
]

ALIASES = {
    # gpt-3.5
    "gpt-3.5-turbo": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    # gpt-4
    "gpt-4-turbo": "gpt-4-turbo-2024-04-09",
    "gpt-4-turbo-preview": "gpt-4-0125-preview",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
}


class Model:
    name = None

    weak_model_name = "gpt-3.5-turbo-0125"

    edit_format = "whole"
    use_repo_map = False
    send_undo_reply = False

    max_chat_history_tokens = 1024
    weak_model = None

    def __init__(self, model):
        self.name = model

        try:
            self.info = litellm.get_model_info(model)
        except Exception as err:
            raise NoModelInfo(str(err))

        if self.info.get("max_input_tokens", 0) < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024

        self.configure_model_settings(model)

    def configure_model_settings(self, model):
        for ms in MODEL_SETTINGS:
            # direct match, or match "provider/<model>"
            if model == ms.name or model.endswith("/" + ms.name):
                for field in fields(ModelSettings):
                    val = getattr(ms, field.name)
                    setattr(self, field.name, val)

                return  # <--

        if "gpt-4" in model or "claude-2" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True

            return  # <--

        # use the defaults

    def __str__(self):
        return self.name

    def get_weak_model(self):
        if not self.weak_model:
            self.weak_model = Model(self.weak_model_name)
        return self.weak_model

    def commit_message_models(self):
        return [self.get_weak_model()]

    def tokenizer(self, text):
        return litellm.encode(model=self.name, text=text)

    def token_count(self, messages):
        if not self.tokenizer:
            return

        if type(messages) is str:
            msgs = messages
        else:
            msgs = json.dumps(messages)

        return len(self.tokenizer(msgs))

    def token_count_for_image(self, fname):
        """
        Calculate the token cost for an image assuming high detail.
        The token cost is determined by the size of the image.
        :param fname: The filename of the image.
        :return: The token cost for the image.
        """
        width, height = self.get_image_size(fname)

        # If the image is larger than 2048 in any dimension, scale it down to fit within 2048x2048
        max_dimension = max(width, height)
        if max_dimension > 2048:
            scale_factor = 2048 / max_dimension
            width = int(width * scale_factor)
            height = int(height * scale_factor)

        # Scale the image such that the shortest side is 768 pixels long
        min_dimension = min(width, height)
        scale_factor = 768 / min_dimension
        width = int(width * scale_factor)
        height = int(height * scale_factor)

        # Calculate the number of 512x512 tiles needed to cover the image
        tiles_width = math.ceil(width / 512)
        tiles_height = math.ceil(height / 512)
        num_tiles = tiles_width * tiles_height

        # Each tile costs 170 tokens, and there's an additional fixed cost of 85 tokens
        token_cost = num_tiles * 170 + 85
        return token_cost

    def get_image_size(self, fname):
        """
        Retrieve the size of an image.
        :param fname: The filename of the image.
        :return: A tuple (width, height) representing the image size in pixels.
        """
        with Image.open(fname) as img:
            return img.size
