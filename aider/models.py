import difflib
import json
import math
import os
import sys
from dataclasses import dataclass, fields
from typing import Optional

import yaml
from PIL import Image

from aider import urls
from aider.dump import dump  # noqa: F401
from aider.litellm import litellm

DEFAULT_MODEL_NAME = "gpt-4o"


@dataclass
class ModelSettings:
    name: str
    edit_format: str
    weak_model_name: Optional[str] = None
    use_repo_map: bool = False
    send_undo_reply: bool = False
    accepts_images: bool = False
    lazy: bool = False
    reminder_as_sys_msg: bool = False
    examples_as_sys_msg: bool = False
    can_prefill: bool = False


# https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
# https://platform.openai.com/docs/models/gpt-3-5-turbo
# https://openai.com/pricing

MODEL_SETTINGS = [
    # gpt-3.5
    ModelSettings(
        "gpt-3.5-turbo",
        "whole",
        weak_model_name="gpt-3.5-turbo",
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-3.5-turbo-0125",
        "whole",
        weak_model_name="gpt-3.5-turbo",
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-3.5-turbo-1106",
        "whole",
        weak_model_name="gpt-3.5-turbo",
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-3.5-turbo-0613",
        "whole",
        weak_model_name="gpt-3.5-turbo",
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-3.5-turbo-16k-0613",
        "whole",
        weak_model_name="gpt-3.5-turbo",
        reminder_as_sys_msg=True,
    ),
    # gpt-4
    ModelSettings(
        "gpt-4-turbo-2024-04-09",
        "udiff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-turbo",
        "udiff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "openai/gpt-4o",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4o",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-0125-preview",
        "udiff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        lazy=True,
        reminder_as_sys_msg=True,
        examples_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-1106-preview",
        "udiff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-vision-preview",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-0314",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        reminder_as_sys_msg=True,
        examples_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-0613",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "gpt-4-32k-0613",
        "diff",
        weak_model_name="gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        reminder_as_sys_msg=True,
    ),
    # Claude
    ModelSettings(
        "claude-3-opus-20240229",
        "diff",
        weak_model_name="claude-3-haiku-20240307",
        use_repo_map=True,
        send_undo_reply=True,
        can_prefill=True,
    ),
    ModelSettings(
        "openrouter/anthropic/claude-3-opus",
        "diff",
        weak_model_name="openrouter/anthropic/claude-3-haiku",
        use_repo_map=True,
        send_undo_reply=True,
        can_prefill=True,
    ),
    ModelSettings(
        "claude-3-sonnet-20240229",
        "whole",
        weak_model_name="claude-3-haiku-20240307",
        can_prefill=True,
    ),
    ModelSettings(
        "claude-3-5-sonnet-20240620",
        "diff",
        weak_model_name="claude-3-haiku-20240307",
        use_repo_map=True,
        examples_as_sys_msg=True,
        can_prefill=True,
        accepts_images=True,
    ),
    ModelSettings(
        "anthropic/claude-3-5-sonnet-20240620",
        "diff",
        weak_model_name="claude-3-haiku-20240307",
        use_repo_map=True,
        examples_as_sys_msg=True,
        can_prefill=True,
    ),
    ModelSettings(
        "openrouter/anthropic/claude-3.5-sonnet",
        "diff",
        weak_model_name="openrouter/anthropic/claude-3-haiku-20240307",
        use_repo_map=True,
        examples_as_sys_msg=True,
        can_prefill=True,
        accepts_images=True,
    ),
    # Vertex AI Claude models
    ModelSettings(
        "vertex_ai/claude-3-5-sonnet@20240620",
        "diff",
        weak_model_name="vertex_ai/claude-3-haiku@20240307",
        use_repo_map=True,
        examples_as_sys_msg=True,
        can_prefill=True,
        accepts_images=True,
    ),
    ModelSettings(
        "vertex_ai/claude-3-opus@20240229",
        "diff",
        weak_model_name="vertex_ai/claude-3-haiku@20240307",
        use_repo_map=True,
        send_undo_reply=True,
        can_prefill=True,
    ),
    ModelSettings(
        "vertex_ai/claude-3-sonnet@20240229",
        "whole",
        weak_model_name="vertex_ai/claude-3-haiku@20240307",
        can_prefill=True,
    ),
    # Cohere
    ModelSettings(
        "command-r-plus",
        "whole",
        weak_model_name="command-r-plus",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    # Groq llama3
    ModelSettings(
        "groq/llama3-70b-8192",
        "diff",
        weak_model_name="groq/llama3-8b-8192",
        use_repo_map=False,
        send_undo_reply=False,
        examples_as_sys_msg=True,
    ),
    # Openrouter llama3
    ModelSettings(
        "openrouter/meta-llama/llama-3-70b-instruct",
        "diff",
        weak_model_name="openrouter/meta-llama/llama-3-70b-instruct",
        use_repo_map=False,
        send_undo_reply=False,
        examples_as_sys_msg=True,
    ),
    # Gemini
    ModelSettings(
        "gemini/gemini-1.5-pro",
        "diff-fenced",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "gemini/gemini-1.5-pro-latest",
        "diff-fenced",
        use_repo_map=True,
        send_undo_reply=True,
    ),
    ModelSettings(
        "deepseek/deepseek-chat",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
        examples_as_sys_msg=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "deepseek/deepseek-coder",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
        examples_as_sys_msg=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "openrouter/deepseek/deepseek-coder",
        "diff",
        use_repo_map=True,
        send_undo_reply=True,
        examples_as_sys_msg=True,
        reminder_as_sys_msg=True,
    ),
    ModelSettings(
        "openrouter/openai/gpt-4o",
        "diff",
        weak_model_name="openrouter/openai/gpt-3.5-turbo",
        use_repo_map=True,
        send_undo_reply=True,
        accepts_images=True,
        lazy=True,
        reminder_as_sys_msg=True,
    ),
]


class Model:
    name = None

    edit_format = "whole"
    use_repo_map = False
    send_undo_reply = False
    accepts_images = False
    weak_model_name = None
    lazy = False
    reminder_as_sys_msg = False
    examples_as_sys_msg = False

    max_chat_history_tokens = 1024
    weak_model = None

    def __init__(self, model, weak_model=None):
        self.name = model

        # Do we have the model_info?
        try:
            self.info = litellm.get_model_info(model)
        except Exception:
            self.info = dict()

        if not self.info and "gpt-4o" in self.name:
            self.info = {
                "max_tokens": 4096,
                "max_input_tokens": 128000,
                "max_output_tokens": 4096,
                "input_cost_per_token": 5e-06,
                "output_cost_per_token": 1.5e-5,
                "litellm_provider": "openai",
                "mode": "chat",
                "supports_function_calling": True,
                "supports_parallel_function_calling": True,
                "supports_vision": True,
            }

        # Are all needed keys/params available?
        res = self.validate_environment()
        self.missing_keys = res.get("missing_keys")
        self.keys_in_environment = res.get("keys_in_environment")

        max_input_tokens = self.info.get("max_input_tokens")
        if not max_input_tokens:
            max_input_tokens = 0
        if max_input_tokens < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024

        self.configure_model_settings(model)
        if weak_model is False:
            self.weak_model_name = None
        else:
            self.get_weak_model(weak_model)

    def configure_model_settings(self, model):
        for ms in MODEL_SETTINGS:
            # direct match, or match "provider/<model>"
            if model == ms.name:
                for field in fields(ModelSettings):
                    val = getattr(ms, field.name)
                    setattr(self, field.name, val)
                return  # <--

        model = model.lower()

        if ("llama3" in model or "llama-3" in model) and "70b" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True
            self.examples_as_sys_msg = True
            return  # <--

        if "gpt-4-turbo" in model or ("gpt-4-" in model and "-preview" in model):
            self.edit_format = "udiff"
            self.use_repo_map = True
            self.send_undo_reply = True
            return  # <--

        if "gpt-4" in model or "claude-3-opus" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True
            return  # <--

        if "gpt-3.5" in model or "gpt-4" in model:
            self.reminder_as_sys_msg = True

        if "anthropic" in model:
            self.can_prefill = True

        if "3.5-sonnet" in model or "3-5-sonnet" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.examples_as_sys_msg = True
            self.can_prefill = True

        # use the defaults
        if self.edit_format == "diff":
            self.use_repo_map = True

    def __str__(self):
        return self.name

    def get_weak_model(self, provided_weak_model_name):
        # If weak_model_name is provided, override the model settings
        if provided_weak_model_name:
            self.weak_model_name = provided_weak_model_name

        if not self.weak_model_name:
            self.weak_model = self
            return

        if self.weak_model_name == self.name:
            self.weak_model = self
            return

        self.weak_model = Model(
            self.weak_model_name,
            weak_model=False,
        )
        return self.weak_model

    def commit_message_models(self):
        return [self.weak_model]

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

    def validate_environment(self):
        # https://github.com/BerriAI/litellm/issues/3190

        model = self.name
        res = litellm.validate_environment(model)
        if res["keys_in_environment"]:
            return res
        if res["missing_keys"]:
            return res

        provider = self.info.get("litellm_provider", "").lower()
        if provider == "cohere_chat":
            return validate_variables(["COHERE_API_KEY"])
        if provider == "gemini":
            return validate_variables(["GEMINI_API_KEY"])
        if provider == "groq":
            return validate_variables(["GROQ_API_KEY"])

        return res


def register_models(model_settings_fnames):
    files_loaded = []
    for model_settings_fname in model_settings_fnames:
        if not os.path.exists(model_settings_fname):
            continue

        try:
            with open(model_settings_fname, "r") as model_settings_file:
                model_settings_list = yaml.safe_load(model_settings_file)

            for model_settings_dict in model_settings_list:
                model_settings = ModelSettings(**model_settings_dict)
                existing_model_settings = next(
                    (ms for ms in MODEL_SETTINGS if ms.name == model_settings.name), None
                )

                if existing_model_settings:
                    MODEL_SETTINGS.remove(existing_model_settings)
                MODEL_SETTINGS.append(model_settings)
        except Exception as e:
            raise Exception(f"Error loading model settings from {model_settings_fname}: {e}")
        files_loaded.append(model_settings_fname)

    return files_loaded


def register_litellm_models(model_fnames):
    files_loaded = []
    for model_fname in model_fnames:
        if not os.path.exists(model_fname):
            continue

        try:
            with open(model_fname, "r") as model_def_file:
                model_def = json.load(model_def_file)
            litellm.register_model(model_def)
        except Exception as e:
            raise Exception(f"Error loading model definition from {model_fname}: {e}")

        files_loaded.append(model_fname)

    return files_loaded


def validate_variables(vars):
    missing = []
    for var in vars:
        if var not in os.environ:
            missing.append(var)
    if missing:
        return dict(keys_in_environment=False, missing_keys=missing)
    return dict(keys_in_environment=True, missing_keys=missing)


def sanity_check_models(io, main_model):
    sanity_check_model(io, main_model)
    if main_model.weak_model and main_model.weak_model is not main_model:
        sanity_check_model(io, main_model.weak_model)


def sanity_check_model(io, model):
    show = False

    if model.missing_keys:
        show = True
        io.tool_error(f"Model {model}: Missing these environment variables:")
        for key in model.missing_keys:
            io.tool_error(f"- {key}")
    elif not model.keys_in_environment:
        show = True
        io.tool_output(f"Model {model}: Unknown which environment variables are required.")

    if not model.info:
        show = True
        io.tool_output(
            f"Model {model}: Unknown context window size and costs, using sane defaults."
        )

        possible_matches = fuzzy_match_models(model.name)
        if possible_matches:
            io.tool_output("Did you mean one of these?")
            for match in possible_matches:
                fq, m = match
                if fq == m:
                    io.tool_output(f"- {m}")
                else:
                    io.tool_output(f"- {m} ({fq})")

    if show:
        io.tool_output(f"For more info, see: {urls.model_warnings}\n")


def fuzzy_match_models(name):
    name = name.lower()

    chat_models = []
    for model, attrs in litellm.model_cost.items():
        model = model.lower()
        if attrs.get("mode") != "chat":
            continue
        provider = (attrs["litellm_provider"] + "/").lower()

        if model.startswith(provider):
            fq_model = model
        else:
            fq_model = provider + model

        chat_models.append((fq_model, model))

    # exactly matching model
    # matching_models = [
    #    (fq,m) for fq,m in chat_models
    #    if name == fq or name == m
    # ]
    # if matching_models:
    #    return matching_models

    # Check for model names containing the name
    matching_models = [(fq, m) for fq, m in chat_models if name in fq]
    if matching_models:
        return matching_models

    # Check for slight misspellings
    models = [m for fq, m in chat_models]
    matching_models = difflib.get_close_matches(name, models, n=3, cutoff=0.8)
    if matching_models:
        return list(zip(matching_models, matching_models))

    fq_models = [fq for fq, m in chat_models]
    matching_models = difflib.get_close_matches(name, fq_models, n=3, cutoff=0.8)
    return list(zip(matching_models, matching_models))


def print_matching_models(io, search):
    matches = fuzzy_match_models(search)
    if matches:
        io.tool_output(f'Models which match "{search}":')
        for model in matches:
            fq, m = model
            if fq == m:
                io.tool_output(f"- {m}")
            else:
                io.tool_output(f"- {m} ({fq})")
    else:
        io.tool_output(f'No models match "{search}".')


def main():
    if len(sys.argv) != 2:
        print("Usage: python models.py <model_name>")
        sys.exit(1)

    model_name = sys.argv[1]
    matching_models = fuzzy_match_models(model_name)

    if matching_models:
        print(f"Matching models for '{model_name}':")
        for model in matching_models:
            print(model)
    else:
        print(f"No matching models found for '{model_name}'.")


if __name__ == "__main__":
    main()
