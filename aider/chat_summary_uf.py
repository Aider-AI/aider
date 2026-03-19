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
        self._fed_count = 0
        self._init_context_window()

    def _init_context_window(self):
        self._context_window = ContextWindow(
            embedder=TFIDFEmbedder(),
            summarizer=ClusterSummarizer(self.models),
            graduate_at=26,
            max_cold_clusters=10,
            merge_threshold=0.15,
        )
        self._fed_count = 0

    @property
    def context_window(self):
        return self._context_window

    def summarize(self, messages, depth=0):
        if not self.too_big(messages):
            return messages

        # Stale detection: messages shrank → previous result applied → rebuild
        if self._fed_count > len(messages):
            self._init_context_window()

        # Feed only new user/assistant messages, tracking their indices
        fed_indices = []
        for i, msg in enumerate(messages[self._fed_count:], start=self._fed_count):
            role = msg.get("role", "").upper()
            if role not in ("USER", "ASSISTANT"):
                continue
            content = msg.get("content", "")
            if content:
                self.context_window.append(f"# {role}\n{content}")
                fed_indices.append(i)
        self._fed_count = len(messages)

        # If no cold clusters yet, force-graduate the oldest half of hot zone.
        # This breaks the deadlock where too_big fires before graduate_at is reached.
        if self.context_window.cold_count == 0 and self.context_window.hot_count > 4:
            self.context_window.force_graduate(keep_hot=max(4, self.context_window.hot_count // 2))

        # Resolve dirty clusters, then render fresh summaries
        try:
            self.context_window.resolve_dirty()
        except (ValueError, Exception):
            # Cluster summarization failed — fall back to recursive
            return super().summarize(messages, depth)
        rendered = self.context_window.render()

        # Format output
        # hot_count is based on fed user/assistant messages, not all messages.
        # Map back to original message indices to get the right tail.
        hot_count = self.context_window.hot_count
        if hot_count > 0 and hot_count < len(rendered):
            cold_parts = rendered[:-hot_count]
            summary_text = prompts.summary_prefix + "\n\n".join(cold_parts)
            # Find the original message index where hot zone starts
            all_fed = self._get_fed_indices(messages)
            if hot_count <= len(all_fed):
                hot_start = all_fed[-hot_count]
                hot_messages = messages[hot_start:]
            else:
                hot_messages = messages[-hot_count:]
            result = [
                {"role": "user", "content": summary_text},
                {"role": "assistant", "content": "Ok."},
                *hot_messages,
            ]
        else:
            # Not enough messages to form cold clusters.
            # Fall back to recursive — don't return unchanged.
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

    def summarize_all(self, messages):
        return super().summarize_all(messages)
