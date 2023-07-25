import re
from aider.claude.anthropic_model import AnthropicModel

known_tokens = {
    "gpt-3.5-turbo": 4,
    "gpt-4": 8,
    "claude2": 100,
    "claude": 100,
}


class Sender:
    def __init__(self, model):
        self.model = model

    def send(self, message):
        # implementation of send functionality
        pass


class Model:
    always_available = False
    use_repo_map = False

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

            sender = Sender(self)
            sender.send("GPT-4 model initialized")

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

            sender = Sender(self)
            sender.send("GPT-3.5 Turbo model initialized")

            if tokens == 100:
                self.prompt_price = 0.0015
                self.completion_price = 0.002
            elif tokens == 100:
                self.prompt_price = 0.003
                self.completion_price = 0.004
            else:
                anthropic = AnthropicModel()
                self.isclaude = anthropic.check_tokens(name)

            if self.isclaude:
                sender = Sender(self)
                sender.send("Claude model initialized")
            return

        raise ValueError(f"Unsupported model: {name}")

    def is_gpt4(self):
        return self.name.startswith("gpt-4")

    def is_gpt35(self):
        return self.name.startswith("gpt-3.5-turbo")

    def is_claude(self):
        return self.name.startswith("claude")

    def __str__(self):
        return self.name


GPT4 = Model("gpt-4")
GPT35 = Model("gpt-3.5-turbo")
GPT35_16k = Model("gpt-3.5-turbo-16k")
CLAUDE = Model("claude-instant-1.1")
CLAUDE2 = Model("claude-2.0")
