import os

from aider import urls


def select_default_model(args, io, analytics):
    """
    Selects a default model based on available API keys if no model is specified.

    Args:
        args: The command line arguments object.
        io: The InputOutput object for user interaction.
        analytics: The Analytics object for tracking events.

    Returns:
        The name of the selected model, or None if no suitable default is found.
    """
    if args.model:
        return args.model  # Model already specified

    # Select model based on available API keys
    model_key_pairs = [
        ("ANTHROPIC_API_KEY", "sonnet"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("OPENROUTER_API_KEY", "openrouter/anthropic/claude-3.7-sonnet"),
        ("OPENAI_API_KEY", "gpt-4o"),
        ("GEMINI_API_KEY", "gemini/gemini-2.5-pro-exp-03-25"),
        ("VERTEXAI_PROJECT", "vertex_ai/gemini-2.5-pro-exp-03-25"),
    ]

    selected_model = None
    for env_key, model_name in model_key_pairs:
        if os.environ.get(env_key):
            selected_model = model_name
            io.tool_warning(f"Using {model_name} model with {env_key} environment variable.")
            # Track which API key was used for auto-selection
            analytics.event("auto_model_selection", api_key=env_key)
            break

    if not selected_model:
        io.tool_error("You need to specify a --model and an --api-key to use.")
        io.offer_url(urls.models_and_keys, "Open documentation url for more info?")
        analytics.event("auto_model_selection", api_key=None)
        return None

    return selected_model
