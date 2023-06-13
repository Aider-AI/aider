class Model_GPT4_32k:
    name = "gpt-4-32k"
    max_context_tokens = 32 * 1024
    edit_format = "diff"


GPT4_32k = Model_GPT4_32k()


class Model_GPT4:
    name = "gpt-4"
    max_context_tokens = 8 * 1024
    edit_format = "diff"


GPT4 = Model_GPT4()


class Model_GPT35:
    name = "gpt-3.5-turbo"
    max_context_tokens = 4 * 1024
    edit_format = "whole"


GPT35 = Model_GPT35()


class Model_GPT35_16k:
    name = "gpt-3.5-turbo-16k"
    max_context_tokens = 16 * 1024
    edit_format = "whole"


GPT35_16k = Model_GPT35_16k()

GPT35_models = [GPT35, GPT35_16k]
GPT4_models = [GPT4, GPT4_32k]


def get_model(name):
    models = GPT35_models + GPT4_models

    for model in models:
        if model.name == name:
            return model

    raise ValueError(f"Unsupported model: {name}")
