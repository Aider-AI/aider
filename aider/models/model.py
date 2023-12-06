import json


class Model:
    name = None
    edit_format = None
    max_context_tokens = 0
    tokenizer = None
    max_chat_history_tokens = 1024

    always_available = False
    use_repo_map = False
    send_undo_reply = False

    prompt_price = None
    completion_price = None

    @classmethod
    def create(cls, name, client=None):
        from .openai import OpenAIModel
        from .openrouter import OpenRouterModel

        if client and client.base_url.host == "openrouter.ai":
            return OpenRouterModel(client, name)
        return OpenAIModel(name)

    def __str__(self):
        return self.name

    @staticmethod
    def strong_model():
        return Model.create("gpt-4")

    @staticmethod
    def weak_model():
        return Model.create("gpt-3.5-turbo-1106")

    @staticmethod
    def commit_message_models():
        return [Model.weak_model()]

    def token_count(self, messages):
        if not self.tokenizer:
            return

        if type(messages) is str:
            msgs = messages
        else:
            msgs = json.dumps(messages)

        return len(self.tokenizer.encode(msgs))
