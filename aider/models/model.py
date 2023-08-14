import importlib

using_openrouter = False

class Model:
    name = None
    edit_format = None
    max_context_tokens = 0
    tokenizer = None

    always_available = False
    use_repo_map = False
    send_undo_reply = False

    prompt_price = None
    completion_price = None

    def __init__(self, name, openai=None):
        global using_openrouter
        if (openai and "openrouter.ai" in openai.api_base):
            using_openrouter = True

        from .openai import OpenAIModel
        from .openrouter import OpenRouterModel
        model = None
        if using_openrouter:
            if name == 'gpt-4':
                name = 'openai/gpt-4'
            elif name == 'gpt-3.5-turbo':
                name = 'openai/gpt-3.5-turbo'
            elif name == 'gpt-3.5.turbo-16k':
                name = 'openai/gpt-3.5-turbo-16k'

            model = OpenRouterModel(name, openai)
        else:
            model = OpenAIModel(name)

        self.name = model.name
        self.edit_format = model.edit_format
        self.max_context_tokens = model.max_context_tokens
        self.tokenizer = model.tokenizer
        self.prompt_price = model.prompt_price
        self.completion_price = model.completion_price
        self.always_available = model.always_available
        self.use_repo_map = model.use_repo_map

    def __str__(self):
        return self.name

    @staticmethod
    def strong_model():
        return Model('gpt-4')

    @staticmethod
    def weak_model():
        return Model('gpt-3.5-turbo')

    @staticmethod
    def commit_message_models():
        return [Model('gpt-3.5-turbo'), Model('gpt-3.5-turbo-16k')]
