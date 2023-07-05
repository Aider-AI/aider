class Model:
    always_available = False
    use_repo_map = False
    send_undo_reply = False

    prompt_price = None
    completion_price = None

    def __init__(self, name, tokens, edit_format):
        self.name = name
        self.edit_format = edit_format

        if tokens is None:
            raise ValueError(f"Unknown context window size for model: {name}")

        self.max_context_tokens = tokens * 1024

        if self.is_gpt4():
            self.use_repo_map = True
            self.send_undo_reply = True

            if tokens == 8:
                self.prompt_price = 0.03
                self.completion_price = 0.06
            elif tokens == 32:
                self.prompt_price = 0.06
                self.completion_price = 0.12

            return

        if self.is_gpt35():
            self.always_available = True

            if tokens == 4:
                self.prompt_price = 0.0015
                self.completion_price = 0.002
            elif tokens == 16:
                self.prompt_price = 0.003
                self.completion_price = 0.004

            return

        return

    def is_gpt4(self):
        return self.name.startswith("gpt-4")

    def is_gpt35(self):
        return self.name.startswith("gpt-3.5-turbo")

    def __str__(self):
        return self.name


GPT4 = Model("gpt-4", 8, "diff")
GPT35 = Model("gpt-3.5-turbo", 4, "whole")
GPT35_16k = Model("gpt-3.5-turbo-16k", 4, "whole")


def get_model(name):
    if name == GPT4.name:
        return GPT4
    elif name == GPT35.name:
        return GPT35
    elif name == GPT35_16k:
        return GPT35_16k

    raise ValueError(f"No such model: {name}")
