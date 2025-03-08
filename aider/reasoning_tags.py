#!/usr/bin/env python

import re

from aider.dump import dump  # noqa

# Standard tag identifier
REASONING_TAG = "thinking-content-" + "7bbeb8e1441453ad999a0bbba8a46d4b"
# Output formatting
REASONING_START = "> Thinking ..."
REASONING_END = "> ... done thinking.\n\n------"


def replace_reasoning_tags(text, tag_name):
    """
    Replace opening and closing reasoning tags with standard formatting.
    Ensures exactly one blank line before START and END markers.

    Args:
        text (str): The text containing the tags
        tag_name (str): The name of the tag to replace

    Returns:
        str: Text with reasoning tags replaced with standard format
    """
    if not text:
        return text

    # Replace opening tag with proper spacing
    text = re.sub(f"\\s*<{tag_name}>\\s*", f"\n{REASONING_START}\n\n", text)

    # Replace closing tag with proper spacing
    text = re.sub(f"\\s*</{tag_name}>\\s*", f"\n\n{REASONING_END}\n\n", text)

    return text


def format_reasoning_content(reasoning_content, tag_name):
    """
    Format reasoning content with appropriate tags.

    Args:
        reasoning_content (str): The content to format
        tag_name (str): The tag name to use

    Returns:
        str: Formatted reasoning content with tags
    """
    if not reasoning_content:
        return ""

    formatted = f"<{tag_name}>\n\n{reasoning_content}\n\n</{tag_name}>"
    return formatted
