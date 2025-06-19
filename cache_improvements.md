# Gemini Implicit Caching Improvements

## Goal

To improve the effectiveness of implicit prompt caching for language models like Google's Gemini. This is achieved by reordering the components of the prompt sent to the model to maximize the length of the stable, cacheable prefix.

## Factors

Implicit caching provides cost savings when the beginning of a prompt (the "prefix") is identical to a previous request. The longer the common prefix, the greater the savings. To leverage this, we must order the components of Aider's prompt from most-static to most-dynamic.

The components of the Aider prompt and their stability are:

1.  **System Prompt**: The most stable component. It is set once and does not change during a session.
2.  **Read-only File Contents**: Highly stable. The content of these files does not change.
3.  **Read-write (Editable) File Contents**: Relatively stable. The content of these files is a snapshot of their state *before* the current turn's edits are applied. They only change after the model responds and an edit is made.
4.  **Conversation History**: This is a list of messages that grows each turn. For prefix caching, this is quite stable, as the existing history remains unchanged at the start of the list. The cache will cover the entire history from the previous turn.
5.  **Repo Map**: The stability is variable. In the default `auto` mode, the repo map is **highly dynamic**, as its content is regenerated and optimized for every single turn. This makes it less stable than the growing conversation history.
6.  **User's New Input**: The most dynamic component, as it is unique to every turn.

## Decision

To maximize the cacheable prefix, the prompt components must be ordered to place the most stable content blocks first. The conversation history is more cache-friendly than the repo map because it grows predictably, preserving its prefix.

The optimal order is:

1.  System Prompt (`system`, `examples`)
2.  Read-only Files (`readonly_files`)
3.  Editable Files (`chat_files`)
4.  Conversation History (`done`)
5.  Repo Map (`repo`)
6.  Current User Input (`cur`, `reminder`)

This structure `[System Prompt] -> [All File Content] -> [History] -> [Repo Map] -> [User Input]` ensures that on turns without code edits, the cache will hit the system prompt, all file content, and the previous turns' history. On turns with code edits, the cache will still hit the system prompt. This provides the best balance for caching effectiveness.

## Proposed Changes

The implementation requires modifying `aider/coders/chat_chunks.py` to assemble the prompt components in the new order and to ensure existing explicit caching functionality is not broken.

1.  **Modify `all_messages()` in `aider/coders/chat_chunks.py`**:
    *   The method will be updated to concatenate the message chunks in the decided optimal order.

2.  **Adjust `add_cache_control_headers()` in `aider/coders/chat_chunks.py`**:
    *   The logic for applying explicit cache headers (for providers like Anthropic) will be updated to align with the new message order. It will define three cacheable blocks: the system prompt, all file contents, and the repo map.
