import openai


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

    @classmethod
    def create(cls, name):
        from .openai import OpenAIModel
        from .openrouter import OpenRouterModel

        if "openrouter.ai" in openai.api_base:
            return OpenRouterModel(name)
        return OpenAIModel(name)

    def __str__(self):
        return self.name

    @staticmethod
    def strong_model():
        return Model.create("gpt-4")

    @staticmethod
    def weak_model():
        return Model.create("gpt-3.5-turbo")

    @staticmethod
    def commit_message_models():
        return [Model.create("gpt-3.5-turbo"), Model.create("gpt-3.5-turbo-16k")]
