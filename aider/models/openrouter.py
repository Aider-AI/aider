import tiktoken
from .model import Model


class OpenRouterModel(Model):
    def __init__(self, name, openai):
        self.name = name
        self.edit_format = "diff"
        self.use_repo_map = True

        # TODO: figure out proper encodings for non openai models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        available_models = openai.Model.list().data
        found = next((details for details in available_models if details.get('id') == name), None)

        if found:
            self.max_context_tokens = int(found.context_length)
            self.prompt_price = float(found.get('pricing').get('prompt')) * 1000
            self.completion_price = float(found.get('pricing').get('completion')) * 1000

        else:
            raise ValueError('invalid openrouter model for {name}')
