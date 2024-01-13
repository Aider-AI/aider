from .model import Model
from .openai import OpenAIModel
from .openrouter import OpenRouterModel

GPT4 = Model.create("gpt-4")
GPT4_0613 = Model.create("gpt-4-0613")
GPT4_1106_PREVIEW = Model.create("gpt-4-1106-preview")
GPT35 = Model.create("gpt-3.5-turbo")
GPT35_1106 = Model.create("gpt-3.5-turbo-1106")
GPT35_16k = Model.create("gpt-3.5-turbo-16k")

__all__ = [
    OpenAIModel,
    OpenRouterModel,
    GPT4,
    GPT35,
    GPT35_16k,
]
