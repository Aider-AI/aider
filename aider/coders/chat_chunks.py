from dataclasses import dataclass, field
from typing import List


@dataclass
class ChatChunks:
    system: List = field(default_factory=list)
    examples: List = field(default_factory=list)
    done: List = field(default_factory=list)
    repo: List = field(default_factory=list)
    readonly_files: List = field(default_factory=list)
    chat_files: List = field(default_factory=list)
    cur: List = field(default_factory=list)
    reminder: List = field(default_factory=list)
    chunk_ordering: List = field(default_factory=list)

    def __init__(self, chunk_ordering=None):
        self.chunk_ordering = chunk_ordering

    def all_messages(self):
        if self.chunk_ordering:
            messages = []
            for chunk_name in self.chunk_ordering:
                chunk = getattr(self, chunk_name, [])
                if chunk:
                    messages.extend(chunk)
            return messages
        else:
            return (
                self.system
                + self.examples
                + self.readonly_files
                + self.chat_files
                + self.repo
                + self.done
                + self.cur
                + self.reminder
            )

    def add_cache_control_headers(self):
        if self.examples:
            self.add_cache_control(self.examples)
        else:
            self.add_cache_control(self.system)

        # The files form a cacheable block.
        # The block starts with readonly_files and ends with chat_files.
        # So we mark the end of chat_files.
        self.add_cache_control(self.chat_files)

        # The repo map is its own cacheable block.
        self.add_cache_control(self.repo)

        # The history is ephemeral on its own.
        self.add_cache_control(self.done)

    def add_cache_control(self, messages):
        if not messages:
            return

        content = messages[-1]["content"]
        if type(content) is str:
            content = dict(
                type="text",
                text=content,
            )
        content["cache_control"] = {"type": "ephemeral"}

        messages[-1]["content"] = [content]

    def cacheable_messages(self):
        messages = self.all_messages()
        for i, message in enumerate(reversed(messages)):
            if isinstance(message.get("content"), list) and message["content"][0].get(
                "cache_control"
            ):
                return messages[: len(messages) - i]
        return messages
