import json

import tiktoken
from prompt_toolkit.completion import Completion

from aider import prompts

from .dump import dump  # noqa: F401


class ChatSummary:
    def __init__(self, model, max_tokens=1024):
        self.tokenizer = tiktoken.encoding_for_model(model)
        self.max_tokens = max_tokens

    def summarize(self, messages):
        num = len(messages)
        if num < 2:
            return messages

        total = 0
        sized = []
        for msg in messages:
            tokens = len(self.tokenizer.encode(json.dumps(msg)))
            sized.append((tokens, msg))
            total += tokens

        if total <= self.max_tokens:
            return messages

        num = num // 2

        # we want the head to end with an assistant msg
        if messages[num]["role"] == "assistant":
            num += 1

        head = messages[:num]
        tail = messages[num:]

        summary = self.summarize_all(head)

        tail_tokens = sum(tokens for tokens, msg in sized[num:])
        summary_tokens = len(self.tokenizer.encode(json.dumps(summary)))

        result = summary + tail
        if summary_tokens + tail_tokens < self.max_tokens:
            return result

        return self.summarize(result)

    def summarize_all(self, messages):
        content = ""
        for msg in messages:
            role = msg["role"].upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            content += f"# {role}\n"
            content += msg["content"]
            if not content.endswith("\n"):
                content += "\n"

        dump(content)

        messages = [
            dict(role="system", content=prompts.summarize),
            dict(role="user", content=content),
        ]

        summary = simple_send_with_retries(model=models.GPT35.name, messages=messages)
        dump(summary)
