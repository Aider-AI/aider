from aider.dump import dump  # noqa: F401
from aider.utils import format_messages


def sanity_check_messages(messages):
    """Check if messages alternate between user and assistant roles.
    System messages can be interspersed anywhere.
    Also verifies the last non-system message is from the user.
    Returns True if valid, False otherwise."""
    last_role = None
    last_non_system_role = None

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue

        if last_role and role == last_role:
            turns = format_messages(messages)
            raise ValueError("Messages don't properly alternate user/assistant:\n\n" + turns)

        last_role = role
        last_non_system_role = role

    # Ensure last non-system message is from user
    return last_non_system_role == "user"


def ensure_alternating_roles(messages):
    """Ensure messages alternate between 'assistant' and 'user' roles.

    Inserts empty messages of the opposite role when consecutive messages
    of the same 'user' or 'assistant' role are found. Messages with other
    roles (e.g. 'system', 'tool') are ignored by the alternation logic.

    Also handles tool call sequences properly - when an assistant message
    contains tool_calls, processes the complete tool sequence atomically.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.

    Returns:
        List of messages with alternating roles.
    """
    if not messages:
        return messages

    result = []
    i = 0
    n = len(messages)
    prev_role = None

    while i < n:
        msg = messages[i]
        role = msg.get("role")

        # Handle tool call sequences atomically
        if role == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            # Start of tool sequence - collect all related messages
            tool_sequence = [msg]
            expected_ids = {call["id"] for call in msg["tool_calls"]}
            i += 1

            # Collect tool responses
            while i < n and expected_ids:
                next_msg = messages[i]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in expected_ids:
                    tool_sequence.append(next_msg)
                    expected_ids.discard(next_msg.get("tool_call_id"))
                    i += 1
                else:
                    break

            # Add missing tool responses as empty
            for tool_id in expected_ids:
                tool_sequence.append({"role": "tool", "tool_call_id": tool_id, "content": ""})

            # Add the complete tool sequence to result
            for tool_msg in tool_sequence:
                result.append(tool_msg)

            # Update prev_role to assistant after processing tool sequence
            prev_role = "assistant"
            continue

        # Handle normal message alternation
        if role in ("user", "assistant"):
            if role == prev_role:
                # Insert empty message of opposite role
                opposite_role = "user" if role == "assistant" else "assistant"
                result.append({"role": opposite_role, "content": ""})
                prev_role = opposite_role

            result.append(msg)
            prev_role = role
        else:
            # For non-user/assistant roles, just add them directly
            result.append(msg)

        i += 1

    # Consolidate consecutive empty messages in a single pass
    consolidated = []
    for msg in result:
        if not consolidated:
            consolidated.append(msg)
            continue

        last_msg = consolidated[-1]
        current_role = msg.get("role")
        last_role = last_msg.get("role")

        # Skip consecutive empty messages with the same role
        if (
            current_role in ("user", "assistant")
            and last_role in ("user", "assistant")
            and current_role == last_role
            and msg.get("content") == ""
            and last_msg.get("content") == ""
        ):
            continue

        consolidated.append(msg)

    return consolidated
