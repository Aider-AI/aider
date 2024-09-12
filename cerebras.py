"""
This is an aider configuration to use Cerebras.

Please set the CEREBRAS_API_KEY environment variable.

See https://inference-docs.cerebras.ai/introduction for more information.
"""

import os
from aider.coders import OpenAICoder

def get_coder():
    return OpenAICoder(
        api_base="https://api.cerebras.ai/v1",
        model="openai/llama3.1-70b",  # or "openai/Llama-3.1-8B"
        api_key=os.environ.get("CEREBRAS_API_KEY"),
        max_tokens=4096,
        context_window=8192,
    )

