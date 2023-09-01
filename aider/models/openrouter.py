import openai
import tiktoken

from .model import Model

cached_model_details = None


class OpenRouterModel(Model):
    def __init__(self, name):
        if name == "gpt-4":
            name = "openai/gpt-4"
        elif name == "gpt-3.5-turbo":
            name = "openai/gpt-3.5-turbo"
        elif name == "gpt-3.5-turbo-16k":
            name = "openai/gpt-3.5-turbo-16k"

        self.name = name
        self.edit_format = edit_format_for_model(name)
        self.use_repo_map = self.edit_format == "diff"

        # TODO: figure out proper encodings for non openai models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        global cached_model_details
        if cached_model_details is None:
            cached_model_details = openai.Model.list().data
        found = next(
            (details for details in cached_model_details if details.get("id") == name), None
        )

        if found:
            self.max_context_tokens = int(found.get("context_length"))
            self.prompt_price = round(float(found.get("pricing").get("prompt")) * 1000, 6)
            self.completion_price = round(float(found.get("pricing").get("completion")) * 1000, 6)

        else:
            raise ValueError(f"invalid openrouter model: {name}")


# TODO run benchmarks and figure out which models support which edit-formats
def edit_format_for_model(name):
    if any(str in name for str in ["gpt-4", "claude-2"]):
        return "diff"

    return "whole"
