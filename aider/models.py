class Model:
    def __init__(self, name, max_context_tokens):
        self.name = name
        self.max_context_tokens = max_context_tokens * 1024


# 4

GPT4_32k = Model("gpt-4-32k", 32)
GPT4_32k_0613 = Model("gpt-4-32k-0613", 32)
GPT4 = Model("gpt-4", 8)

GPT4_models = [GPT4, GPT4_32k, GPT4_32k_0613]

# 3.5

GPT35 = Model("gpt-3.5-turbo", 4)
GPT35_16k = Model("gpt-3.5-turbo-16k", 16)

GPT35_models = [GPT35, GPT35_16k]


import re

def get_model(name):
    models = GPT35_models + GPT4_models

    for model in models:
        if model.name == name:
            return model

    match = re.search(r'-([0-9]+)k', name)
    tokens = int(match.group(1)) if match else 0

    model = Model(name, tokens)

    if name.startswith("gpt-4-"):
        GPT4_models.append(model)
    elif name.startswith("gpt-3.5-"):
        GPT35_models.append(model)
    else:
        raise ValueError(f"Unsupported model: {name}")

    return model
