import tiktoken
from .model import Model


class OpenRouterModel(Model):
    def __init__(self, name, openai):
        if name == 'gpt-4':
            name = 'openai/gpt-4'
        elif name == 'gpt-3.5-turbo':
            name = 'openai/gpt-3.5-turbo'
        elif name == 'gpt-3.5-turbo-16k':
            name = 'openai/gpt-3.5-turbo-16k'

        self.name = name
        self.edit_format = edit_format_for_model(name)
        self.use_repo_map = self.edit_format == "diff"

        # TODO: figure out proper encodings for non openai models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # TODO cache the model list data to speed up using multiple models
        available_models = openai.Model.list().data
        found = next((details for details in available_models if details.get('id') == name), None)

        if found:
            self.max_context_tokens = int(found.context_length)
            self.prompt_price = float(found.get('pricing').get('prompt')) * 1000
            self.completion_price = float(found.get('pricing').get('completion')) * 1000

        else:
            raise ValueError(f'invalid openrouter model: {name}')


# TODO run benchmarks and figure out which models support which edit-formats
def edit_format_for_model(name):
    if any(str in name for str in ['gpt-4', 'claude-2']):
        return "diff"

    return "whole"
