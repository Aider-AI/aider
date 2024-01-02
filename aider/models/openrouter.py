import tiktoken

from .model import Model

cached_model_details = None


class OpenRouterModel(Model):
    def __init__(self, client, name):
        if name.startswith("gpt-4") or name.startswith("gpt-3.5-turbo"):
            name = "openai/" + name

        self.name = name
        self.edit_format = edit_format_for_model(name)
        self.use_repo_map = self.edit_format == "diff"

        # TODO: figure out proper encodings for non openai models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        global cached_model_details
        if cached_model_details is None:
            cached_model_details = client.models.list().data
        found = next(
            (details for details in cached_model_details if details.id == name), None
        )

        if found:
            self.max_context_tokens = int(found.context_length)
            self.prompt_price = round(float(found.pricing.get("prompt")) * 1000, 6)
            self.completion_price = round(float(found.pricing.get("completion")) * 1000, 6)

        else:
            raise ValueError(f"invalid openrouter model: {name}")


def edit_format_for_model(name):
    if any(str in name for str in ["gpt-4", "claude-2"]):
        return "diff"

    return "whole"
