from aider.dump import dump  # noqa: F401
from aider.utils import format_messages


def sanity_check_messages(messages):
    """Check if messages alternate between user and assistant roles.
    System messages can be interspersed anywhere.
    Also verifies the last non-system message is from the user.
    Validates tool message sequences.
    Returns True if valid, False otherwise."""
    last_role = None
    last_non_system_role = None
    i = 0
    n = len(messages)

    while i < n:
        msg = messages[i]
        role = msg.get("role")

        # Handle tool sequences atomically
        if role == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            # Validate tool sequence
            expected_ids = {call["id"] for call in msg["tool_calls"]}
            i += 1

            # Check for tool responses
            while i < n and expected_ids:
                next_msg = messages[i]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in expected_ids:
                    expected_ids.discard(next_msg.get("tool_call_id"))
                    i += 1
                else:
                    break

            # If we still have expected IDs, the tool sequence is incomplete
            if expected_ids:
                turns = format_messages(messages)
                raise ValueError(
                    "Incomplete tool sequence - missing responses for tool calls:\n\n" + turns
                )

            # Continue to next message after tool sequence
            continue

        elif role == "tool":
            # Orphaned tool message without preceding assistant tool_calls
            turns = format_messages(messages)
            raise ValueError(
                "Orphaned tool message without preceding assistant tool_calls:\n\n" + turns
            )

        # Handle normal role alternation
        if role == "system":
            i += 1
            continue

        if last_role and role == last_role:
            turns = format_messages(messages)
            raise ValueError("Messages don't properly alternate user/assistant:\n\n" + turns)

        last_role = role
        last_non_system_role = role
        i += 1

    # Ensure last non-system message is from user
    return last_non_system_role == "user"


def clean_orphaned_tool_messages(messages):
    """Remove orphaned tool messages and incomplete tool sequences.

    This function removes:
    - Tool messages without a preceding assistant message containing tool_calls
    - Assistant messages with tool_calls that don't have complete tool responses

    Args:
        messages: List of message dictionaries

    Returns:
        Cleaned list of messages with orphaned tool sequences removed
    """
    if not messages:
        return messages

    cleaned = []
    i = 0
    n = len(messages)

    while i < n:
        msg = messages[i]
        role = msg.get("role")

        # If it's an assistant message with tool_calls, check if we have complete responses
        if role == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            # Start of potential tool sequence
            tool_sequence = [msg]
            expected_ids = {call["id"] for call in msg["tool_calls"]}
            j = i + 1

            # Collect tool responses
            while j < n and expected_ids:
                next_msg = messages[j]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in expected_ids:
                    tool_sequence.append(next_msg)
                    expected_ids.discard(next_msg.get("tool_call_id"))
                    j += 1
                else:
                    break

            # If we have all tool responses, keep the sequence
            if not expected_ids:
                cleaned.extend(tool_sequence)
                i = j
            else:
                # Incomplete sequence - skip the entire tool sequence
                i = j
                # Don't add anything to cleaned
                continue

        elif role == "tool":
            # Orphaned tool message without preceding assistant tool_calls - skip it
            i += 1
            continue
        else:
            # Regular message - add it
            cleaned.append(msg)
            i += 1

    return cleaned


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

    # First clean orphaned tool messages
    messages = clean_orphaned_tool_messages(messages)

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
                tool_sequence.append(
                    {"role": "tool", "tool_call_id": tool_id, "content": "(empty response)"}
                )

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
                result.append(
                    {
                        "role": opposite_role,
                        "content": (
                            "(empty response)"
                            if opposite_role == "assistant"
                            else "(empty request)"
                        ),
                    }
                )
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
            and msg.get("content") in ["", "(empty response)", "(empty request)"]
            and last_msg.get("content") in ["", "(empty response)", "(empty request)"]
        ):
            continue

        consolidated.append(msg)

    return consolidated
