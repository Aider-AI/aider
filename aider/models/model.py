import json
import math

import litellm
from PIL import Image

from aider.dump import dump


class Model:
    name = None
    edit_format = "whole"

    use_repo_map = False
    send_undo_reply = False
    max_chat_history_tokens = 1024

    def __init__(self, model):
        self.name = model
        self.info = litellm.get_model_info(model)
        dump(self.info)

        if self.info.get("max_input_tokens", 0) < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024

    def __str__(self):
        return self.name

    def weak_model(self):
        model = "gpt-3.5-turbo-0125"
        if self.name == model:
            return self

        return Model(model)

    def commit_message_models(self):
        return [self.weak_model()]

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
