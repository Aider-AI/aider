class Model_GPT4_32k:
    name = "gpt-4-32k"
    max_context_tokens = 32 * 1024


GPT4_32k = Model_GPT4_32k()


class Model_GPT4:
    name = "gpt-4"
    max_context_tokens = 8 * 1024


GPT4 = Model_GPT4()


class Model_GPT35:
    name = "gpt-3.5-turbo"
    max_context_tokens = 4 * 1024


GPT35 = Model_GPT35()


class Model_GPT35_16k:
    name = "gpt-3.5-turbo-16k"
    max_context_tokens = 16 * 1024


GPT35 = Model_GPT35_16k()


def get_model(name):
    models = [
        GPT4_32k,
        GPT4,
        GPT35,
    ]

    for model in models:
        if model.name == name:
            return model

    raise ValueError(f"Unsupported model: {name}")
