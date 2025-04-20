#!/usr/bin/env python

import json
from pathlib import Path

import json5


def main():
    script_dir = Path(__file__).parent.resolve()
    litellm_path = script_dir / "../../litellm/model_prices_and_context_window.json"
    aider_path = script_dir / "../aider/resources/model-metadata.json"

    if not litellm_path.exists():
        print(f"Error: LiteLLM metadata file not found at {litellm_path}")
        return

    if not aider_path.exists():
        print(f"Error: Aider metadata file not found at {aider_path}")
        return

    try:
        with open(litellm_path, "r") as f:
            litellm_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {litellm_path}: {e}")
        return
    except Exception as e:
        print(f"Error reading {litellm_path}: {e}")
        return

    try:
        # Use json5 for the aider metadata file as it might contain comments
        with open(aider_path, "r") as f:
            aider_data = json5.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {aider_path}: {e}")
        return
    except Exception as e:
        print(f"Error reading {aider_path}: {e}")
        return

    litellm_keys = set(litellm_data.keys())
    aider_keys = set(aider_data.keys())

    common_keys = litellm_keys.intersection(aider_keys)

    if common_keys:
        print("Common models found in both files:")
        for key in sorted(list(common_keys)):
            print(f"- {key}")
    else:
        print("No common models found between the two files.")


if __name__ == "__main__":
    main()
