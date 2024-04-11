import pkg_resources
import logging
import tiktoken

from .model import Model

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('aider-litellm')

LITELLM_VERSION = None
try:
  LITELLM_VERSION = pkg_resources.get_distribution("litellm").version
except pkg_resources.DistributionNotFound:
  pass

def is_litellm_installed():
  return LITELLM_VERSION is not None

model_aliases = {
    # claude-3
    "opus": "claude-3-opus-20240229",
    "sonnet": "claude-3-sonnet-20240229",
    "haiku": "claude-3-haiku-20240307",
    # gemini-1.5-pro
    "gemini": "gemini-1.5-pro-preview-0409",
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

        global models_info
        if not models_info:
          models_info = fetchModelsInfo()

        model_data = models_info.get(model_id)
        if not model_data:
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

# Returns a JSON object where each key is a model name and each model name
# points to a JSON object. See the following example:
#
#     "gemini/gemini-1.5-pro": {
#        "max_tokens": 8192,
#        "max_input_tokens": 1000000,
#        "max_output_tokens": 8192,
#        "input_cost_per_token": 0, 
#        "output_cost_per_token": 0,
#        "litellm_provider": "gemini",
#        "mode": "chat",
#        "supports_function_calling": true,
#        "source": "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models#foundation_models"
#      }
#
# The 'source', 'mode', and 'supports_function_calling' properties may not
# exist.
#
def fetchModelsInfo():
  import requests
  import json

  global LITELLM_VERSION
  if LITELLM_VERSION is None:
    logger.error("LiteLLM not installed. Please run 'pip install litellm' first.")
    return {}

  logger.info(f"Found LiteLLM version: {LITELLM_VERSION}")
  supported_models_url = f"https://raw.githubusercontent.com/BerriAI/litellm/v{LITELLM_VERSION}/model_prices_and_context_window.json"

  try:
    logger.info(f"Fetching supported models from {supported_models_url}")
    response = requests.get(supported_models_url)

    if response.status_code == 200:
      return json.loads(response.text)

    logger.error(f"Request failed with status code {response.status_code}")
    return {}

  except Exception as e:
    logger.error(f"Failed to fetch models info: {str(e)}")
    return {}
