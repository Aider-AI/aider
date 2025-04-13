import difflib
import hashlib
import importlib.resources
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional, Union

import json5
import yaml
from PIL import Image

from aider.dump import dump  # noqa: F401
from aider.llm import litellm
from aider.sendchat import ensure_alternating_roles, sanity_check_messages
from aider.utils import check_pip_install_extra

RETRY_TIMEOUT = 60

request_timeout = 600

DEFAULT_MODEL_NAME = "gpt-4o"
ANTHROPIC_BETA_HEADER = "prompt-caching-2024-07-31,pdfs-2024-09-25"

OPENAI_MODELS = """
o1
o1-preview
o1-mini
o3-mini
gpt-4
gpt-4o
gpt-4o-2024-05-13
gpt-4-turbo-preview
gpt-4-0314
gpt-4-0613
gpt-4-32k
gpt-4-32k-0314
gpt-4-32k-0613
gpt-4-turbo
gpt-4-turbo-2024-04-09
gpt-4-1106-preview
gpt-4-0125-preview
gpt-4-vision-preview
gpt-4-1106-vision-preview
gpt-4o-mini
gpt-4o-mini-2024-07-18
gpt-3.5-turbo
gpt-3.5-turbo-0301
gpt-3.5-turbo-0613
gpt-3.5-turbo-1106
gpt-3.5-turbo-0125
gpt-3.5-turbo-16k
gpt-3.5-turbo-16k-0613
"""

OPENAI_MODELS = [ln.strip() for ln in OPENAI_MODELS.splitlines() if ln.strip()]

ANTHROPIC_MODELS = """
claude-2
claude-2.1
claude-3-haiku-20240307
claude-3-5-haiku-20241022
claude-3-opus-20240229
claude-3-sonnet-20240229
claude-3-5-sonnet-20240620
claude-3-5-sonnet-20241022
"""

ANTHROPIC_MODELS = [ln.strip() for ln in ANTHROPIC_MODELS.splitlines() if ln.strip()]

# Mapping of model aliases to their canonical names
MODEL_ALIASES = {
    # Claude models
    "sonnet": "anthropic/claude-3-7-sonnet-20250219",
    "haiku": "claude-3-5-haiku-20241022",
    "opus": "claude-3-opus-20240229",
    # GPT models
    "4": "gpt-4-0613",
    "4o": "gpt-4o",
    "4-turbo": "gpt-4-1106-preview",
    "35turbo": "gpt-3.5-turbo",
    "35-turbo": "gpt-3.5-turbo",
    "3": "gpt-3.5-turbo",
    # Other models
    "deepseek": "deepseek/deepseek-chat",
    "flash": "gemini/gemini-2.0-flash-exp",
    "quasar": "openrouter/openrouter/quasar-alpha",
    "r1": "deepseek/deepseek-reasoner",
    "gemini-2.5-pro": "gemini/gemini-2.5-pro-exp-03-25",
    "gemini": "gemini/gemini-2.5-pro-preview-03-25",
    "gemini-exp": "gemini/gemini-2.5-pro-exp-03-25",
    "grok3": "xai/grok-3-beta",
    "optimus": "openrouter/openrouter/optimus-alpha",
}
# Model metadata loaded from resources and user's files.


@dataclass
class ModelSettings:
    # Model class needs to have each of these as well
    name: str
    edit_format: str = "whole"
    weak_model_name: Optional[str] = None
    use_repo_map: bool = False
    send_undo_reply: bool = False
    lazy: bool = False
    overeager: bool = False
    reminder: str = "user"
    examples_as_sys_msg: bool = False
    extra_params: Optional[dict] = None
    cache_control: bool = False
    caches_by_default: bool = False
    use_system_prompt: bool = True
    use_temperature: Union[bool, float] = True
    streaming: bool = True
    editor_model_name: Optional[str] = None
    editor_edit_format: Optional[str] = None
    reasoning_tag: Optional[str] = None
    remove_reasoning: Optional[str] = None  # Deprecated alias for reasoning_tag
    system_prompt_prefix: Optional[str] = None
    accepts_settings: Optional[list] = None


# Load model settings from package resource
MODEL_SETTINGS = []
with importlib.resources.open_text("aider.resources", "model-settings.yml") as f:
    model_settings_list = yaml.safe_load(f)
    for model_settings_dict in model_settings_list:
        MODEL_SETTINGS.append(ModelSettings(**model_settings_dict))


class ModelInfoManager:
    MODEL_INFO_URL = (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/"
        "model_prices_and_context_window.json"
    )
    CACHE_TTL = 60 * 60 * 24  # 24 hours

    def __init__(self):
        self.cache_dir = Path.home() / ".aider" / "caches"
        self.cache_file = self.cache_dir / "model_prices_and_context_window.json"
        self.content = None
        self.local_model_metadata = {}
        self.verify_ssl = True
        self._cache_loaded = False

    def set_verify_ssl(self, verify_ssl):
        self.verify_ssl = verify_ssl

    def _load_cache(self):
        if self._cache_loaded:
            return

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if self.cache_file.exists():
                cache_age = time.time() - self.cache_file.stat().st_mtime
                if cache_age < self.CACHE_TTL:
                    try:
                        self.content = json.loads(self.cache_file.read_text())
                    except json.JSONDecodeError:
                        # If the cache file is corrupted, treat it as missing
                        self.content = None
        except OSError:
            pass

        self._cache_loaded = True

    def _update_cache(self):
        try:
            import requests

            # Respect the --no-verify-ssl switch
            response = requests.get(self.MODEL_INFO_URL, timeout=5, verify=self.verify_ssl)
            if response.status_code == 200:
                self.content = response.json()
                try:
                    self.cache_file.write_text(json.dumps(self.content, indent=4))
                except OSError:
                    pass
        except Exception as ex:
            print(str(ex))
            try:
                # Save empty dict to cache file on failure
                self.cache_file.write_text("{}")
            except OSError:
                pass

    def get_model_from_cached_json_db(self, model):
        data = self.local_model_metadata.get(model)
        if data:
            return data

        # Ensure cache is loaded before checking content
        self._load_cache()

        if not self.content:
            self._update_cache()

        if not self.content:
            return dict()

        info = self.content.get(model, dict())
        if info:
            return info

        pieces = model.split("/")
        if len(pieces) == 2:
            info = self.content.get(pieces[1])
            if info and info.get("litellm_provider") == pieces[0]:
                return info

        return dict()

    def get_model_info(self, model):
        cached_info = self.get_model_from_cached_json_db(model)

        litellm_info = None
        if litellm._lazy_module or not cached_info:
            try:
                litellm_info = litellm.get_model_info(model)
            except Exception as ex:
                if "model_prices_and_context_window.json" not in str(ex):
                    print(str(ex))

        if litellm_info:
            return litellm_info

        return cached_info


model_info_manager = ModelInfoManager()


class Model(ModelSettings):
    def __init__(
        self, model, weak_model=None, editor_model=None, editor_edit_format=None, verbose=False
    ):
        # Map any alias to its canonical name
        model = MODEL_ALIASES.get(model, model)

        self.name = model
        self.verbose = verbose

        self.max_chat_history_tokens = 1024
        self.weak_model = None
        self.editor_model = None

        # Find the extra settings
        self.extra_model_settings = next(
            (ms for ms in MODEL_SETTINGS if ms.name == "aider/extra_params"), None
        )

        self.info = self.get_model_info(model)

        # Are all needed keys/params available?
        res = self.validate_environment()
        self.missing_keys = res.get("missing_keys")
        self.keys_in_environment = res.get("keys_in_environment")

        max_input_tokens = self.info.get("max_input_tokens") or 0
        # Calculate max_chat_history_tokens as 1/16th of max_input_tokens,
        # with minimum 1k and maximum 8k
        self.max_chat_history_tokens = min(max(max_input_tokens / 16, 1024), 8192)

        self.configure_model_settings(model)
        if weak_model is False:
            self.weak_model_name = None
        else:
            self.get_weak_model(weak_model)

        if editor_model is False:
            self.editor_model_name = None
        else:
            self.get_editor_model(editor_model, editor_edit_format)

    def get_model_info(self, model):
        return model_info_manager.get_model_info(model)

    def _copy_fields(self, source):
        """Helper to copy fields from a ModelSettings instance to self"""
        for field in fields(ModelSettings):
            val = getattr(source, field.name)
            setattr(self, field.name, val)

        # Handle backward compatibility: if remove_reasoning is set but reasoning_tag isn't,
        # use remove_reasoning's value for reasoning_tag
        if self.reasoning_tag is None and self.remove_reasoning is not None:
            self.reasoning_tag = self.remove_reasoning

    def configure_model_settings(self, model):
        # Look for exact model match
        exact_match = False
        for ms in MODEL_SETTINGS:
            # direct match, or match "provider/<model>"
            if model == ms.name:
                self._copy_fields(ms)
                exact_match = True
                break  # Continue to apply overrides

        # Initialize accepts_settings if it's None
        if self.accepts_settings is None:
            self.accepts_settings = []

        model = model.lower()

        # If no exact match, try generic settings
        if not exact_match:
            self.apply_generic_model_settings(model)

        # Apply override settings last if they exist
        if self.extra_model_settings and self.extra_model_settings.extra_params:
            # Initialize extra_params if it doesn't exist
            if not self.extra_params:
                self.extra_params = {}

            # Deep merge the extra_params dicts
            for key, value in self.extra_model_settings.extra_params.items():
                if isinstance(value, dict) and isinstance(self.extra_params.get(key), dict):
                    # For nested dicts, merge recursively
                    self.extra_params[key] = {**self.extra_params[key], **value}
                else:
                    # For non-dict values, simply update
                    self.extra_params[key] = value

    def apply_generic_model_settings(self, model):
        if "/o3-mini" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.use_temperature = False
            self.system_prompt_prefix = "Formatting re-enabled. "
            if "reasoning_effort" not in self.accepts_settings:
                self.accepts_settings.append("reasoning_effort")
            return  # <--

        if "/o1-mini" in model:
            self.use_repo_map = True
            self.use_temperature = False
            self.use_system_prompt = False
            return  # <--

        if "/o1-preview" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.use_temperature = False
            self.use_system_prompt = False
            return  # <--

        if "/o1" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.use_temperature = False
            self.streaming = False
            self.system_prompt_prefix = "Formatting re-enabled. "
            if "reasoning_effort" not in self.accepts_settings:
                self.accepts_settings.append("reasoning_effort")
            return  # <--

        if "deepseek" in model and "v3" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.reminder = "sys"
            self.examples_as_sys_msg = True
            return  # <--

        if "deepseek" in model and ("r1" in model or "reasoning" in model):
            self.edit_format = "diff"
            self.use_repo_map = True
            self.examples_as_sys_msg = True
            self.use_temperature = False
            self.reasoning_tag = "think"
            return  # <--

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
            self.reminder = "sys"
            return  # <--

        if "3-7-sonnet" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.examples_as_sys_msg = True
            self.reminder = "user"
            if "thinking_tokens" not in self.accepts_settings:
                self.accepts_settings.append("thinking_tokens")
            return  # <--

        if "3.5-sonnet" in model or "3-5-sonnet" in model:
            self.edit_format = "diff"
            self.use_repo_map = True
            self.examples_as_sys_msg = True
            self.reminder = "user"
            return  # <--

        if model.startswith("o1-") or "/o1-" in model:
            self.use_system_prompt = False
            self.use_temperature = False
            return  # <--

        if (
            "qwen" in model
            and "coder" in model
            and ("2.5" in model or "2-5" in model)
            and "32b" in model
        ):
            self.edit_format = "diff"
            self.editor_edit_format = "editor-diff"
            self.use_repo_map = True
            return  # <--

        if "qwq" in model and "32b" in model and "preview" not in model:
            self.edit_format = "diff"
            self.editor_edit_format = "editor-diff"
            self.use_repo_map = True
            self.reasoning_tag = "think"
            self.examples_as_sys_msg = True
            self.use_temperature = 0.6
            self.extra_params = dict(top_p=0.95)
            return  # <--

        # use the defaults
        if self.edit_format == "diff":
            self.use_repo_map = True
            return  # <--

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
        return [self.weak_model, self]

    def get_editor_model(self, provided_editor_model_name, editor_edit_format):
        # If editor_model_name is provided, override the model settings
        if provided_editor_model_name:
            self.editor_model_name = provided_editor_model_name
        if editor_edit_format:
            self.editor_edit_format = editor_edit_format

        if not self.editor_model_name or self.editor_model_name == self.name:
            self.editor_model = self
        else:
            self.editor_model = Model(
                self.editor_model_name,
                editor_model=False,
            )

        if not self.editor_edit_format:
            self.editor_edit_format = self.editor_model.edit_format
            if self.editor_edit_format in ("diff", "whole", "diff-fenced"):
                self.editor_edit_format = "editor-" + self.editor_edit_format

        return self.editor_model

    def tokenizer(self, text):
        return litellm.encode(model=self.name, text=text)

    def token_count(self, messages):
        if type(messages) is list:
            try:
                return litellm.token_counter(model=self.name, messages=messages)
            except Exception as err:
                print(f"Unable to count tokens: {err}")
                return 0

        if not self.tokenizer:
            return

        if type(messages) is str:
            msgs = messages
        else:
            msgs = json.dumps(messages)

        try:
            return len(self.tokenizer(msgs))
        except Exception as err:
            print(f"Unable to count tokens: {err}")
            return 0

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

    def fast_validate_environment(self):
        """Fast path for common models. Avoids forcing litellm import."""

        model = self.name

        pieces = model.split("/")
        if len(pieces) > 1:
            provider = pieces[0]
        else:
            provider = None

        keymap = dict(
            openrouter="OPENROUTER_API_KEY",
            openai="OPENAI_API_KEY",
            deepseek="DEEPSEEK_API_KEY",
            gemini="GEMINI_API_KEY",
            anthropic="ANTHROPIC_API_KEY",
            groq="GROQ_API_KEY",
            fireworks_ai="FIREWORKS_API_KEY",
        )
        var = None
        if model in OPENAI_MODELS:
            var = "OPENAI_API_KEY"
        elif model in ANTHROPIC_MODELS:
            var = "ANTHROPIC_API_KEY"
        else:
            var = keymap.get(provider)

        if var and os.environ.get(var):
            return dict(keys_in_environment=[var], missing_keys=[])

    def validate_environment(self):
        res = self.fast_validate_environment()
        if res:
            return res

        # https://github.com/BerriAI/litellm/issues/3190

        model = self.name
        res = litellm.validate_environment(model)

        # If missing AWS credential keys but AWS_PROFILE is set, consider AWS credentials valid
        if res["missing_keys"] and any(
            key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"] for key in res["missing_keys"]
        ):
            if model.startswith("bedrock/") or model.startswith("us.anthropic."):
                if os.environ.get("AWS_PROFILE"):
                    res["missing_keys"] = [
                        k
                        for k in res["missing_keys"]
                        if k not in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
                    ]
                    if not res["missing_keys"]:
                        res["keys_in_environment"] = True

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

    def get_repo_map_tokens(self):
        map_tokens = 1024
        max_inp_tokens = self.info.get("max_input_tokens")
        if max_inp_tokens:
            map_tokens = max_inp_tokens / 8
            map_tokens = min(map_tokens, 4096)
            map_tokens = max(map_tokens, 1024)
        return map_tokens

    def set_reasoning_effort(self, effort):
        """Set the reasoning effort parameter for models that support it"""
        if effort is not None:
            if not self.extra_params:
                self.extra_params = {}
            if "extra_body" not in self.extra_params:
                self.extra_params["extra_body"] = {}
            self.extra_params["extra_body"]["reasoning_effort"] = effort

    def parse_token_value(self, value):
        """
        Parse a token value string into an integer.
        Accepts formats: 8096, "8k", "10.5k", "0.5M", "10K", etc.

        Args:
            value: String or int token value

        Returns:
            Integer token value
        """
        if isinstance(value, int):
            return value

        if not isinstance(value, str):
            return int(value)  # Try to convert to int

        value = value.strip().upper()

        if value.endswith("K"):
            multiplier = 1024
            value = value[:-1]
        elif value.endswith("M"):
            multiplier = 1024 * 1024
            value = value[:-1]
        else:
            multiplier = 1

        # Convert to float first to handle decimal values like "10.5k"
        return int(float(value) * multiplier)

    def set_thinking_tokens(self, value):
        """
        Set the thinking token budget for models that support it.
        Accepts formats: 8096, "8k", "10.5k", "0.5M", "10K", etc.
        """
        if value is not None:
            num_tokens = self.parse_token_value(value)
            self.use_temperature = False
            if not self.extra_params:
                self.extra_params = {}

            # OpenRouter models use 'reasoning' instead of 'thinking'
            if self.name.startswith("openrouter/"):
                self.extra_params["reasoning"] = {"max_tokens": num_tokens}
            else:
                self.extra_params["thinking"] = {"type": "enabled", "budget_tokens": num_tokens}

    def get_raw_thinking_tokens(self):
        """Get formatted thinking token budget if available"""
        budget = None

        if self.extra_params:
            # Check for OpenRouter reasoning format
            if "reasoning" in self.extra_params and "max_tokens" in self.extra_params["reasoning"]:
                budget = self.extra_params["reasoning"]["max_tokens"]
            # Check for standard thinking format
            elif (
                "thinking" in self.extra_params and "budget_tokens" in self.extra_params["thinking"]
            ):
                budget = self.extra_params["thinking"]["budget_tokens"]

        return budget

    def get_thinking_tokens(self):
        budget = self.get_raw_thinking_tokens()

        if budget is not None:
            # Format as xx.yK for thousands, xx.yM for millions
            if budget >= 1024 * 1024:
                value = budget / (1024 * 1024)
                if value == int(value):
                    return f"{int(value)}M"
                else:
                    return f"{value:.1f}M"
            else:
                value = budget / 1024
                if value == int(value):
                    return f"{int(value)}k"
                else:
                    return f"{value:.1f}k"
        return None

    def get_reasoning_effort(self):
        """Get reasoning effort value if available"""
        if (
            self.extra_params
            and "extra_body" in self.extra_params
            and "reasoning_effort" in self.extra_params["extra_body"]
        ):
            return self.extra_params["extra_body"]["reasoning_effort"]
        return None

    def is_deepseek_r1(self):
        name = self.name.lower()
        if "deepseek" not in name:
            return
        return "r1" in name or "reasoner" in name

    def is_ollama(self):
        return self.name.startswith("ollama/") or self.name.startswith("ollama_chat/")

    def send_completion(self, messages, functions, stream, temperature=None):
        if os.environ.get("AIDER_SANITY_CHECK_TURNS"):
            sanity_check_messages(messages)

        if self.is_deepseek_r1():
            messages = ensure_alternating_roles(messages)

        kwargs = dict(
            model=self.name,
            stream=stream,
        )

        if self.use_temperature is not False:
            if temperature is None:
                if isinstance(self.use_temperature, bool):
                    temperature = 0
                else:
                    temperature = float(self.use_temperature)

            kwargs["temperature"] = temperature

        if functions is not None:
            function = functions[0]
            kwargs["tools"] = [dict(type="function", function=function)]
            kwargs["tool_choice"] = {"type": "function", "function": {"name": function["name"]}}
        if self.extra_params:
            kwargs.update(self.extra_params)
        if self.is_ollama() and "num_ctx" not in kwargs:
            num_ctx = int(self.token_count(messages) * 1.25) + 8192
            kwargs["num_ctx"] = num_ctx
        key = json.dumps(kwargs, sort_keys=True).encode()

        # dump(kwargs)

        hash_object = hashlib.sha1(key)
        if "timeout" not in kwargs:
            kwargs["timeout"] = request_timeout
        if self.verbose:
            dump(kwargs)
        kwargs["messages"] = messages

        res = litellm.completion(**kwargs)
        return hash_object, res

    def simple_send_with_retries(self, messages):
        from aider.exceptions import LiteLLMExceptions

        litellm_ex = LiteLLMExceptions()
        if "deepseek-reasoner" in self.name:
            messages = ensure_alternating_roles(messages)
        retry_delay = 0.125

        while True:
            try:
                kwargs = {
                    "messages": messages,
                    "functions": None,
                    "stream": False,
                }

                _hash, response = self.send_completion(**kwargs)
                if not response or not hasattr(response, "choices") or not response.choices:
                    return None
                res = response.choices[0].message.content
                from aider.reasoning_tags import remove_reasoning_content

                return remove_reasoning_content(res, self.reasoning_tag)

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


def register_models(model_settings_fnames):
    files_loaded = []
    for model_settings_fname in model_settings_fnames:
        if not os.path.exists(model_settings_fname):
            continue

        if not Path(model_settings_fname).read_text().strip():
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
            data = Path(model_fname).read_text()
            if not data.strip():
                continue
            model_def = json5.loads(data)
            if not model_def:
                continue

            # Defer registration with litellm to faster path.
            model_info_manager.local_model_metadata.update(model_def)
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
    problem_main = sanity_check_model(io, main_model)

    problem_weak = None
    if main_model.weak_model and main_model.weak_model is not main_model:
        problem_weak = sanity_check_model(io, main_model.weak_model)

    problem_editor = None
    if (
        main_model.editor_model
        and main_model.editor_model is not main_model
        and main_model.editor_model is not main_model.weak_model
    ):
        problem_editor = sanity_check_model(io, main_model.editor_model)

    return problem_main or problem_weak or problem_editor


def sanity_check_model(io, model):
    show = False

    if model.missing_keys:
        show = True
        io.tool_warning(f"Warning: {model} expects these environment variables")
        for key in model.missing_keys:
            value = os.environ.get(key, "")
            status = "Set" if value else "Not set"
            io.tool_output(f"- {key}: {status}")

        if platform.system() == "Windows":
            io.tool_output(
                "Note: You may need to restart your terminal or command prompt for `setx` to take"
                " effect."
            )

    elif not model.keys_in_environment:
        show = True
        io.tool_warning(f"Warning for {model}: Unknown which environment variables are required.")

    # Check for model-specific dependencies
    check_for_dependencies(io, model.name)

    if not model.info:
        show = True
        io.tool_warning(
            f"Warning for {model}: Unknown context window size and costs, using sane defaults."
        )

        possible_matches = fuzzy_match_models(model.name)
        if possible_matches:
            io.tool_output("Did you mean one of these?")
            for match in possible_matches:
                io.tool_output(f"- {match}")

    return show


def check_for_dependencies(io, model_name):
    """
    Check for model-specific dependencies and install them if needed.

    Args:
        io: The IO object for user interaction
        model_name: The name of the model to check dependencies for
    """
    # Check if this is a Bedrock model and ensure boto3 is installed
    if model_name.startswith("bedrock/"):
        check_pip_install_extra(
            io, "boto3", "AWS Bedrock models require the boto3 package.", ["boto3"]
        )

    # Check if this is a Vertex AI model and ensure google-cloud-aiplatform is installed
    elif model_name.startswith("vertex_ai/"):
        check_pip_install_extra(
            io,
            "google.cloud.aiplatform",
            "Google Vertex AI models require the google-cloud-aiplatform package.",
            ["google-cloud-aiplatform"],
        )


def fuzzy_match_models(name):
    name = name.lower()

    chat_models = set()
    model_metadata = list(litellm.model_cost.items())
    model_metadata += list(model_info_manager.local_model_metadata.items())

    for orig_model, attrs in model_metadata:
        model = orig_model.lower()
        if attrs.get("mode") != "chat":
            continue
        provider = attrs.get("litellm_provider", "").lower()
        if not provider:
            continue
        provider += "/"

        if model.startswith(provider):
            fq_model = orig_model
        else:
            fq_model = provider + orig_model

        chat_models.add(fq_model)
        chat_models.add(orig_model)

    chat_models = sorted(chat_models)
    # exactly matching model
    # matching_models = [
    #    (fq,m) for fq,m in chat_models
    #    if name == fq or name == m
    # ]
    # if matching_models:
    #    return matching_models

    # Check for model names containing the name
    matching_models = [m for m in chat_models if name in m]
    if matching_models:
        return sorted(set(matching_models))

    # Check for slight misspellings
    models = set(chat_models)
    matching_models = difflib.get_close_matches(name, models, n=3, cutoff=0.8)

    return sorted(set(matching_models))


def print_matching_models(io, search):
    matches = fuzzy_match_models(search)
    if matches:
        io.tool_output(f'Models which match "{search}":')
        for model in matches:
            io.tool_output(f"- {model}")
    else:
        io.tool_output(f'No models match "{search}".')


def get_model_settings_as_yaml():
    from dataclasses import fields

    import yaml

    model_settings_list = []
    # Add default settings first with all field values
    defaults = {}
    for field in fields(ModelSettings):
        defaults[field.name] = field.default
    defaults["name"] = "(default values)"
    model_settings_list.append(defaults)

    # Sort model settings by name
    for ms in sorted(MODEL_SETTINGS, key=lambda x: x.name):
        # Create dict with explicit field order
        model_settings_dict = {}
        for field in fields(ModelSettings):
            value = getattr(ms, field.name)
            if value != field.default:
                model_settings_dict[field.name] = value
        model_settings_list.append(model_settings_dict)
        # Add blank line between entries
        model_settings_list.append(None)

    # Filter out None values before dumping
    yaml_str = yaml.dump(
        [ms for ms in model_settings_list if ms is not None],
        default_flow_style=False,
        sort_keys=False,  # Preserve field order from dataclass
    )
    # Add actual blank lines between entries
    return yaml_str.replace("\n- ", "\n\n- ")


def main():
    if len(sys.argv) < 2:
        print("Usage: python models.py <model_name> or python models.py --yaml")
        sys.exit(1)

    if sys.argv[1] == "--yaml":
        yaml_string = get_model_settings_as_yaml()
        print(yaml_string)
    else:
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
