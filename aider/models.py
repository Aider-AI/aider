import re

known_tokens = {
    "gpt-3.5-turbo": 4,
    "gpt-4": 8,
}


class Model:
    always_available = False
    use_repo_map = False
    send_undo_reply = False

    prompt_price = None
    completion_price = None

    def __init__(self, name):
        self.name = name

        tokens = None

        match = re.search(r"-([0-9]+)k", name)
        if match:
            tokens = int(match.group(1))
        else:
            for m, t in known_tokens.items():
                if name.startswith(m):
                    tokens = t

        if tokens is None:
            raise ValueError(f"Unknown context window size for model: {name}")

        self.max_context_tokens = tokens * 1024

        if self.is_gpt4():
            self.edit_format = "diff"
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
            self.edit_format = "whole"
            self.always_available = True

            if tokens == 4:
                self.prompt_price = 0.0015
                self.completion_price = 0.002
            elif tokens == 16:
                self.prompt_price = 0.003
                self.completion_price = 0.004

            return

        raise ValueError(f"Unsupported model: {name}")

    def is_gpt4(self):
        return self.name.startswith("gpt-4")

    def is_gpt35(self):
        return self.name.startswith("gpt-3.5-turbo")

    def __str__(self):
        return self.name


GPT4 = Model("gpt-4")
GPT35 = Model("gpt-3.5-turbo")
GPT35_16k = Model("gpt-3.5-turbo-16k")
