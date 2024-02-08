import tiktoken

from .model import Model

cached_model_details = None


class OpenRouterModel(Model):
    def __init__(self, client, name):
        if name.startswith("gpt-4") or name.startswith("gpt-3.5-turbo"):
            if name == 'gpt-4-0613':
                name = 'openai/gpt-4'
            else:
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

    def available_models(self):
        global cached_model_details
        models_dict_format = {}
        for model in cached_model_details:
            model_id = model.id
            aliases = {
                'openai/gpt-4': 'gpt4',
                'openai/gpt-4-1106-preview': '4',
                'openai/gpt-4-vision-preview': '4v',
                'openai/gpt-4-32k-0613': '4-32',
                'openai/gpt-3.5-turbo-0125': '3',
                'anthropic/claude-2': 'claude-2',
                'mistralai/mistral-medium': 'mistral-medium',
                'google/gemini-pro': 'gemini-pro',
                'codellama/codellama-70b-instruct': 'code-llama',
            }
            models_dict_format[model_id] = {
                'Alias': aliases.get(model_id, ''),
                'Model': model_id,
                'Input_cost': round(float(model.pricing.get('prompt')) * 1000, 6),
                'Input_desc': ' / 1K tokens',
                'Input_cur': '$',
                'Output_cost': round(float(model.pricing.get('completion')) * 1000, 6),
                'Output_desc': ' / 1K tokens',
                'Output_cur': '$'
            }
        return models_dict_format

def edit_format_for_model(name):
    if any(str in name for str in ["gpt-4", "claude-2"]):
        return "diff"

    return "whole"
