import argparse

from aider import models, prompts
from aider.dump import dump  # noqa: F401


class ChatSummary:
    def __init__(self, models=None, max_tokens=1024):
        if not models:
            raise ValueError("At least one model must be provided")
        self.models = models if isinstance(models, list) else [models]
        self.max_tokens = max_tokens
        self.token_count = self.models[0].token_count

    def check_max_tokens(self, messages, max_tokens=None):
        if max_tokens is None:
            max_tokens = self.max_tokens

        if not max_tokens:
            return False

        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _msg in sized)
        return total > max_tokens

    def tokenize(self, messages):
        sized = []
        for msg in messages:
            tokens = self.token_count(msg)
            sized.append((tokens, msg))
        return sized

    def summarize(self, messages, depth=0):
        messages = self.summarize_real(messages)
        if messages and messages[-1]["role"] != "assistant":
            messages.append(dict(role="assistant", content="Ok."))
        return messages

    def summarize_real(self, messages, depth=0):
        if not self.models:
            raise ValueError("No models available for summarization")

        sized = self.tokenize(messages)
        total = sum(tokens for tokens, _msg in sized)

        if total <= self.max_tokens:
            if depth == 0:
                # All fit, no summarization needed
                return messages
            # This is a chunk that's small enough to summarize in one go
            return self.summarize_all(messages)

        min_split = 4
        if len(messages) <= min_split or depth > 4:
            return self.summarize_all(messages)

        tail_tokens = 0
        split_index = len(messages)
        half_max_tokens = self.max_tokens // 2

        # Iterate over the messages in reverse order
        for i in range(len(sized) - 1, -1, -1):
            tokens, _msg = sized[i]
            if tail_tokens + tokens < half_max_tokens:
                tail_tokens += tokens
                split_index = i
            else:
                break

        # If we couldn't find a split point from the end, it's because the
        # last message was too big. So just split off the last message and
        # summarize the rest. This prevents infinite recursion.
        if split_index == len(messages):
            split_index = len(messages) - 1

        # Ensure the head ends with an assistant message
        while messages[split_index - 1]["role"] != "assistant" and split_index > 1:
            split_index -= 1

        if split_index <= min_split:
            return self.summarize_all(messages)

        # Split head and tail
        head = messages[:split_index]
        tail = messages[split_index:]

        summary = self.summarize_real(head, depth + 1)

        # If the combined summary and tail still fits, return directly
        new_messages = summary + tail

        sized_new = self.tokenize(new_messages)
        total_new = sum(tokens for tokens, _msg in sized_new)

        if total_new < self.max_tokens:
            return new_messages

        # Otherwise recurse with increased depth
        return self.summarize_real(new_messages, depth + 1)

    def summarize_all(self, messages):
        content = ""
        for msg in messages:
            role = msg["role"].upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            if not msg.get("content"):
                continue
            content += f"# {role}\n"
            content += msg["content"]
            if not content.endswith("\n"):
                content += "\n"

        summarize_messages = [
            dict(role="system", content=prompts.summarize),
            dict(role="user", content=content),
        ]

        for model in self.models:
            try:
                summary = model.simple_send_with_retries(summarize_messages)
                if summary is not None:
                    summary = prompts.summary_prefix + summary
                    return [dict(role="user", content=summary)]
            except Exception as e:
                print(f"Summarization failed for model {model.name}: {str(e)}")

        err = "summarizer unexpectedly failed for all models"
        print(err)
        raise ValueError(err)

    def summarize_all_as_text(self, messages, prompt, max_tokens=None):
        content = ""
        for msg in messages:
            role = msg["role"].upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            if not msg.get("content"):
                continue
            content += f"# {role}\n"
            content += msg["content"]
            if not content.endswith("\n"):
                content += "\n"

        summarize_messages = [
            dict(role="system", content=prompt),
            dict(role="user", content=content),
        ]

        for model in self.models:
            try:
                summary = model.simple_send_with_retries(summarize_messages, max_tokens=max_tokens)
                if summary is not None:
                    return summary
            except Exception as e:
                print(f"Summarization failed for model {model.name}: {str(e)}")

        raise ValueError("summarizer unexpectedly failed for all models")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Markdown file to parse")
    args = parser.parse_args()

    model_names = ["gpt-3.5-turbo", "gpt-4"]  # Add more model names as needed
    model_list = [models.Model(name) for name in model_names]
    summarizer = ChatSummary(model_list)

    with open(args.filename, "r") as f:
        text = f.read()

    summary = summarizer.summarize_chat_history_markdown(text)
    dump(summary)


if __name__ == "__main__":
    main()
