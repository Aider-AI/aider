from ..sendchat import ensure_alternating_roles


def thought_signature(model, messages):
    # Add thought signatures for Vertex AI and Gemini models
    if model.name.startswith("vertex_ai/") or model.name.startswith("gemini/"):
        for msg in messages:
            if "tool_calls" in msg:
                tool_calls = msg["tool_calls"]
                for call in tool_calls:
                    # Check if thought signature is missing in extra_content.google.thought_signature
                    if "provider_specific_fields" not in call:
                        call["provider_specific_fields"] = {}
                    if "thought_signature" not in call["provider_specific_fields"]:
                        call["provider_specific_fields"][
                            "thought_signature"
                        ] = "skip_thought_signature_validator"

            if "function_call" in msg:
                call = msg["function_call"]
                # Check if thought signature is missing in extra_content.google.thought_signature
                if "provider_specific_fields" not in call:
                    call["provider_specific_fields"] = {}
                if "thought_signature" not in call["provider_specific_fields"]:
                    call["provider_specific_fields"][
                        "thought_signature"
                    ] = "skip_thought_signature_validator"

    return messages


def model_request_parser(model, messages):
    messages = thought_signature(model, messages)
    messages = ensure_alternating_roles(messages)

    return messages
