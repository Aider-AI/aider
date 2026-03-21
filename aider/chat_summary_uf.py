"""ChatSummaryUF — drop-in replacement for aider's ChatSummary.

Uses union-find context compaction instead of recursive summarization.
Falls back to recursive when union-find can't improve on the input.
"""

from aider.history import ChatSummary
from aider import prompts

from aider.context_window import ContextWindow
from aider.embedding_service import TFIDFEmbedder
from aider.cluster_summarizer import ClusterSummarizer


class ChatSummaryUF(ChatSummary):
    """Union-find context compaction, subclassing aider's ChatSummary."""

    def __init__(self, models=None, max_tokens=1024):
        super().__init__(models, max_tokens)
        self._fed_messages = []
        self._init_context_window()

    def _init_context_window(self):
        self.context_window = ContextWindow(
            embedder=TFIDFEmbedder(),
            summarizer=ClusterSummarizer(self.models),
            graduate_at=26,
            max_cold_clusters=10,
            merge_threshold=0.15,
        )
        self._fed_messages = []

    @staticmethod
    def _chat_messages(messages):
        """Extract user/assistant messages with non-empty content."""
        return [
            msg for msg in messages
            if msg.get("role", "").upper() in ("USER", "ASSISTANT")
            and msg.get("content", "")
        ]

    def _starts_with_fed(self, chat_msgs):
        """Check if chat_msgs starts with our previously fed messages."""
        if len(chat_msgs) < len(self._fed_messages):
            return False
        for i, msg in enumerate(self._fed_messages):
            if chat_msgs[i] != msg:
                return False
        return True

    def _rebuild(self, chat_msgs):
        """Rebuild context window from scratch when state is stale."""
        self._init_context_window()
        for msg in chat_msgs:
            role = msg.get("role", "").upper()
            content = msg.get("content", "")
            self.context_window.append(f"# {role}\n{content}")
        self._fed_messages = list(chat_msgs)

    def summarize(self, messages, depth=0):
        if not self.too_big(messages):
            return super().summarize(messages, depth)

        chat_msgs = self._chat_messages(messages)

        # Prefix-based stale detection: rebuild if messages changed
        if not self._starts_with_fed(chat_msgs):
            self._rebuild(chat_msgs)
        else:
            # Feed only new messages
            for msg in chat_msgs[len(self._fed_messages):]:
                role = msg.get("role", "").upper()
                content = msg.get("content", "")
                self.context_window.append(f"# {role}\n{content}")
            self._fed_messages = list(chat_msgs)

        # Token-aware graduation: keep only as many hot messages as fit
        # in 25% of the token budget. Graduate the rest to cold clusters.
        if self.context_window.hot_count > 2:
            hot_budget = self.max_tokens // 4
            keep = 0
            for content in reversed(self.context_window.hot_messages()):
                cost = self.token_count({"role": "user", "content": content})
                if hot_budget - cost < 0 and keep >= 2:
                    break
                hot_budget -= cost
                keep += 1
            keep = max(2, keep)
            if keep < self.context_window.hot_count:
                self.context_window.force_graduate(keep_hot=keep)

        # Resolve dirty clusters, then render fresh summaries
        try:
            self.context_window.resolve_dirty()
        except (ValueError, Exception):
            return super().summarize(messages, depth)
        rendered = self.context_window.render()

        # Format output
        # hot_count is based on fed user/assistant messages, not all messages.
        # Map back to original message indices to get the right tail.
        hot_count = self.context_window.hot_count
        if hot_count > 0 and hot_count < len(rendered):
            cold_parts = rendered[:-hot_count]
            summary_text = prompts.summary_prefix + "\n\n".join(cold_parts)
            hot_start = self._get_hot_start(messages, hot_count)
            hot_messages = messages[hot_start:]
            result = [
                {"role": "user", "content": summary_text},
                {"role": "assistant", "content": "Ok."},
                *hot_messages,
            ]
        else:
            return super().summarize(messages, depth)

        # Budget safety: must fit max_tokens AND be smaller than input
        result_tokens = sum(self.token_count(m) for m in result)
        if result_tokens > self.max_tokens:
            return super().summarize(messages, depth)
        input_tokens = sum(self.token_count(m) for m in messages)
        if result_tokens >= input_tokens:
            return super().summarize(messages, depth)

        if result and result[-1]["role"] != "assistant":
            result.append({"role": "assistant", "content": "Ok."})
        return result

    @staticmethod
    def _get_fed_indices(messages):
        """Return indices of user/assistant messages with non-empty content."""
        return [
            i for i, msg in enumerate(messages)
            if msg.get("role", "").upper() in ("USER", "ASSISTANT")
            and msg.get("content", "")
        ]

    @classmethod
    def _get_hot_start(cls, messages, hot_count):
        """Map the hot user/assistant boundary back to the original message list."""
        all_fed = cls._get_fed_indices(messages)
        if hot_count <= 0 or hot_count > len(all_fed):
            return max(0, len(messages) - hot_count)

        hot_start = all_fed[-hot_count]

        # Include boundary system/tool messages immediately before the first hot turn.
        while hot_start > 0:
            role = messages[hot_start - 1].get("role", "").upper()
            if role in ("USER", "ASSISTANT"):
                break
            hot_start -= 1

        # Match the base summarizer behavior: hot tail should begin on a user turn.
        while hot_start > 0 and messages[hot_start].get("role", "").upper() != "USER":
            hot_start -= 1

        return hot_start

    def summarize_all(self, messages):
        return super().summarize_all(messages)
