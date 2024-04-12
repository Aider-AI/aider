import pkg_resources
import logging
import tiktoken
import platform
import os

from .model import Model

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("aider-litellm")

LITELLM_VERSION = None
try:
  LITELLM_VERSION = pkg_resources.get_distribution("litellm").version
except pkg_resources.DistributionNotFound:
  pass

model_aliases = {
    # claude-3
    "opus": "claude-3-opus-20240229",
    "sonnet": "claude-3-sonnet-20240229",
    "haiku": "claude-3-haiku-20240307",
    # gemini-1.5-pro
    "gemini": "gemini/gemini-1.5-pro-latest",
    # gpt-3.5
    "gpt-3.5": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    # gpt-4
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
}

models_info = None

class LiteLLMModel(Model):
    def __init__(self, name):
        model_id = name
        if name in model_aliases:
            model_id = model_aliases[name]

        from litellm import model_cost

        model_data = model_cost.get(model_id)
        if not model_data:
            # For gemini 1.5 pro to work, LiteLLM appears to need the "-latest"
            # part included in the model name, but it's not included in the list
            # of supported models that way, so finesse it here
            if model_id == "gemini/gemini-1.5-pro-latest":
               model_data = model_cost.get("gemini/gemini-1.5-pro")
               if not model_data:
                   raise ValueError(f"Unsupported model: {model_id}")
            else:
                raise ValueError(f"Unsupported model: {model_id}")

        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.name = model_id
        self.max_context_tokens = model_data.get("max_input_tokens")
        self.prompt_price = model_data.get("input_cost_per_token") * 100
        self.completion_price = model_data.get("output_cost_per_token") * 100

        is_high_end = model_id.startswith("gpt-4") or model_id.startswith("claude-3-opus")
        
        self.edit_format = "udiff" if is_high_end else "whole"
        self.use_repo_map = is_high_end
        self.send_undo_reply = is_high_end

        # set the history token limit
        if self.max_context_tokens < 32 * 1024:
            self.max_chat_history_tokens = 1024
        else:
            self.max_chat_history_tokens = 2 * 1024
