from .model import Model
from .openai import OpenAIModel
from .openrouter import OpenRouterModel

GPT4 = Model.create("gpt-4")
GPT4_0613 = Model.create("gpt-4-0613")
GPT35 = Model.create("gpt-3.5-turbo")
GPT35_0125 = Model.create("gpt-3.5-turbo-0125")

__all__ = [
    OpenAIModel,
    OpenRouterModel,
    GPT4,
    GPT35,
    GPT35_0125,
]
