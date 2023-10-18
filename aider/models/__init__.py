from .model import Model
from .openai import OpenAIModel
from .openrouter import OpenRouterModel

GPT4 = Model.create("gpt-4")
GPT35 = Model.create("gpt-3.5-turbo")
GPT35_16k = Model.create("gpt-3.5-turbo-16k")

__all__ = [
    OpenAIModel,
    OpenRouterModel,
    GPT4,
    GPT35,
    GPT35_16k,
]
