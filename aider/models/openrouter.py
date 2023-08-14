import tiktoken
from .model import Model


class OpenRouterModel(Model):
    def __init__(self, name, openai):
        self.name = name
        self.edit_format = "diff"
        self.use_repo_map = True
        self.max_context_tokens = 1024 * 8

        # TODO: figure out proper encodings for non openai models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
