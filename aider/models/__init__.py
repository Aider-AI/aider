from .openai import OpenAIModel
from .openrouter import OpenRouterModel
from .model import Model

GPT4 = Model.create('gpt-4')
GPT35 = Model.create('gpt-3.5-turbo')
GPT35_16k = Model.create('gpt-3.5-turbo-16k')
