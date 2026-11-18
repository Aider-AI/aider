import os

import requests

LOGIN_HINT = (
    "Run `aider --login openrouter` (or another provider) to sign in with your browser,"
    " or set an API key."
)


def check_openrouter_tier(api_key):
    """
    Checks if the user is on a free tier for OpenRouter.

    Args:
        api_key: The OpenRouter API key to check.

    Returns:
        A boolean indicating if the user is on a free tier (True) or paid tier (False).
        Returns True if the check fails.
    """
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,  # Add a reasonable timeout
        )
        response.raise_for_status()
        data = response.json()
        # According to the documentation, 'is_free_tier' will be true if the user has never paid
        return data.get("data", {}).get("is_free_tier", True)  # Default to True if not found
    except Exception:
        # If there's any error, we'll default to assuming free tier
        return True


def try_to_select_default_model():
    """
    Attempts to select a default model based on available API keys.
    Checks OpenRouter tier status to select appropriate model.

    Returns:
        The name of the selected model, or None if no suitable default is found.
    """
    # Special handling for OpenRouter
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        # Check if the user is on a free tier
        is_free_tier = check_openrouter_tier(openrouter_key)
        if is_free_tier:
            return "openrouter/deepseek/deepseek-r1:free"
        else:
            return "openrouter/anthropic/claude-sonnet-4"

    # Select model based on other available API keys
    model_key_pairs = [
        ("ANTHROPIC_API_KEY", "sonnet"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("OPENAI_API_KEY", "gpt-4o"),
        ("GEMINI_API_KEY", "gemini/gemini-2.5-pro-exp-03-25"),
        ("VERTEXAI_PROJECT", "vertex_ai/gemini-2.5-pro-exp-03-25"),
    ]

    for env_key, model_name in model_key_pairs:
        api_key_value = os.environ.get(env_key)
        if api_key_value:
            return model_name

    return None


def select_default_model(args, io, analytics):
    """
    Selects a default model based on available API keys if no model is specified.

    There is no automatic sign-in here. When no key is found, the user is told
    how to sign in with `aider --login openrouter`.

    Args:
        args: The command line arguments object.
        io: The InputOutput object for user interaction.
        analytics: The Analytics object for tracking events.

    Returns:
        The name of the selected model, or None if no suitable default is found.
    """
    if args.model:
        return args.model  # Model already specified

    model = try_to_select_default_model()
    if model:
        io.tool_warning(f"Using {model} model with API key from environment.")
        analytics.event("auto_model_selection", model=model)
        return model

    io.tool_warning(f"No LLM model was specified and no API keys were provided. {LOGIN_HINT}")
    return None
