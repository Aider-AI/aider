import re


class Model:
    always_available = False
    use_repo_map = False
    send_undo_reply = False

    def __init__(self, name, tokens=None):
        self.name = name
        if tokens is None:
            match = re.search(r"-([0-9]+)k", name)

            default_tokens = 8

            tokens = int(match.group(1)) if match else default_tokens

        self.max_context_tokens = tokens * 1024

        if self.is_gpt4():
            self.edit_format = "diff"
            self.use_repo_map = True
            self.send_undo_reply = True
            return

        if self.is_gpt35():
            self.edit_format = "whole"
            self.always_available = True
            return

        raise ValueError(f"Unsupported model: {name}")

    def is_gpt4(self):
        return self.name.startswith("gpt-4")

    def is_gpt35(self):
        return self.name.startswith("gpt-3.5-turbo")


GPT4 = Model("gpt-4", 8)
GPT35 = Model("gpt-3.5-turbo")
GPT35_16k = Model("gpt-3.5-turbo-16k")
