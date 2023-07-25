import re

known_tokens = {"claude-instant-1.1": 100, "claude-2.0": 100}


class AnthropicModel:
    def __init__(self):
        super().__init__()
        self.is_claude = False

    def check_tokens(self, name):
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

        self.max_context_tokens = tokens * 100000

        if self.is_claude11():
            self.edit_format = "whole"
            self.always_available = True
            self.prompt_price = 0.00000163
            self.completion_price = 0.001102
            self.is_claude = True
            return self.is_claude
        if self.is_claude20():
            self.edit_format = "whole"
            self.always_available = True
            self.prompt_price = 0.00000551
            self.completion_price = 0.00003268
            self.is_claude = True
            return self.is_claude
        else:
            raise ValueError(f"Unsupported model: {name}")
