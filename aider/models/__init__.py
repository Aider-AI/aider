from .model import Model
from .openai import OpenAIModel
from .openrouter import OpenRouterModel

GPT4 = Model.create("gpt-4")
GPT35 = Model.create("gpt-3.5-turbo")
GPT35_0125 = Model.create("gpt-3.5-turbo-0125")

DEFAULT_MODEL_NAME = "gpt-4-1106-preview"

__all__ = [
    OpenAIModel,
    OpenRouterModel,
    GPT4,
    GPT35,
    GPT35_0125,
]
