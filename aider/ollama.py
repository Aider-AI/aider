import asyncio
import os

import aiohttp


async def query_available_models():
    api_base = os.getenv("OLLAMA_API_BASE")
    if not api_base:
        return {}

    async with aiohttp.ClientSession() as session:
        # Ping the tags endpoint to get model names
        async with session.get(f"{api_base}/api/tags") as response:
            if response.status != 200:
                return {}

            tags = await response.json()
            model_names = [tag["name"] for tag in tags["models"]]

            # Wait for all model descriptions to complete
            model_descriptions = await asyncio.gather(
                *[describe_ollama_model(model_name) for model_name in model_names]
            )

            # Merge the results into a single dictionary
            result = {}
            for model_desc in model_descriptions:
                result.update(model_desc)

            return result


async def describe_ollama_model(model_name):
    api_base = os.getenv("OLLAMA_API_BASE")
    context_length = None
    async with aiohttp.ClientSession() as session:
        # Ping the /show endpoint to get context length
        async with session.post(f"{api_base}/api/show", json={"model": model_name}) as response:
            if response.status != 200:
                return {}
            json = await response.json()
            model_info = json.get("model_info")
            for key in model_info:
                # Model native context length is usually stored in a key like
                # "llama.context_length" or "qwen3.context_length"
                if "context_length" in key:
                    context_length = model_info[key]
                    break

    return {
        "ollama/"
        + model_name: {
            "max_tokens": context_length,
            "max_input_tokens": context_length,
            "max_output_tokens": context_length,
            "input_cost_per_token": 0,
            "input_cost_per_token_cache_hit": 0,
            "cache_read_input_token_cost": 0,
            "cache_creation_input_token_cost": 0,
            "output_cost_per_token": 0,
            "litellm_provider": "ollama",
            "mode": "chat",
            "supports_function_calling": False,
            "supports_assistant_prefill": False,
            "supports_tool_choice": False,
            "supports_prompt_caching": False,
        }
    }
