"""Double-buffer context management for aider.

Implements a two-phase compaction strategy:
- Checkpoint at configurable threshold (default 60%) of max chat history tokens
- Swap at configurable threshold (default 85%) using pre-computed summary

When the front buffer approaches capacity, a background checkpoint generates
a high-quality summary while the model still has full attention. At the swap
threshold, the pre-computed summary replaces old history seamlessly.

See: https://marklubin.me/posts/hopping-context-windows/
"""

import logging
import threading
from enum import Enum

log = logging.getLogger(__name__)


class Phase(Enum):
    NORMAL = "normal"
    CHECKPOINT_PENDING = "checkpoint_pending"
    CONCURRENT = "concurrent"


class DoubleBufferManager:
    """Manages double-buffer state for a single aider session.

    Integrates with aider's existing ChatSummary for summarization
    and base_coder's done_messages/cur_messages for message management.
    """

    def __init__(
        self,
        checkpoint_threshold=0.60,
        swap_threshold=0.85,
    ):
        if not (0 < checkpoint_threshold < swap_threshold <= 1.0):
            raise ValueError(
                f"Invalid thresholds: checkpoint={checkpoint_threshold}, "
                f"swap={swap_threshold}. Must satisfy 0 < checkpoint < swap <= 1.0"
            )
        self.checkpoint_threshold = checkpoint_threshold
        self.swap_threshold = swap_threshold

        self.phase = Phase.NORMAL
        self.checkpoint_summary = None
        self.checkpoint_done_messages_len = 0
        self.generation = 0

        self._checkpoint_thread = None
        self._checkpoint_messages_snapshot = None
        self._checkpoint_result = None

    def should_checkpoint(self, current_tokens, max_tokens):
        """Check if a background checkpoint should start.

        Args:
            current_tokens: Current token count of done_messages.
            max_tokens: Maximum chat history tokens (model.max_chat_history_tokens).

        Returns:
            True if checkpoint should be triggered.
        """
        if self.phase != Phase.NORMAL:
            return False
        if max_tokens <= 0:
            return False

        threshold = int(max_tokens * self.checkpoint_threshold)
        result = current_tokens >= threshold
        if result:
            log.info(
                "Checkpoint threshold reached: %d tokens >= %d (%d%% of %d)",
                current_tokens,
                threshold,
                int(self.checkpoint_threshold * 100),
                max_tokens,
            )
        return result

    def should_swap(self, current_tokens, max_tokens):
        """Check if buffer swap should occur.

        Args:
            current_tokens: Current token count of done_messages.
            max_tokens: Maximum chat history tokens.

        Returns:
            True if swap should be triggered.
        """
        if self.phase != Phase.CONCURRENT:
            return False
        if self.checkpoint_summary is None:
            return False
        if max_tokens <= 0:
            return False

        threshold = int(max_tokens * self.swap_threshold)
        result = current_tokens >= threshold
        if result:
            log.info(
                "Swap threshold reached: %d tokens >= %d (%d%% of %d), generation=%d",
                current_tokens,
                threshold,
                int(self.swap_threshold * 100),
                max_tokens,
                self.generation,
            )
        return result

    def begin_checkpoint(self, done_messages, summarizer):
        """Start a background checkpoint summarization.

        Args:
            done_messages: Current done_messages list to snapshot.
            summarizer: ChatSummary instance for summarization.
        """
        self.phase = Phase.CHECKPOINT_PENDING
        self._checkpoint_messages_snapshot = list(done_messages)
        self.checkpoint_done_messages_len = len(done_messages)
        self._checkpoint_result = None

        log.info(
            "Checkpoint started: %d messages to summarize",
            len(done_messages),
        )

        self._checkpoint_thread = threading.Thread(
            target=self._run_checkpoint,
            args=(summarizer,),
            daemon=True,
        )
        self._checkpoint_thread.start()

    def _run_checkpoint(self, summarizer):
        """Background thread that generates the checkpoint summary."""
        try:
            result = summarizer.summarize(self._checkpoint_messages_snapshot)
            if result:
                # Extract summary text from the summarized messages
                summary_parts = []
                for msg in result:
                    content = msg.get("content", "")
                    if content:
                        summary_parts.append(content)
                self.checkpoint_summary = "\n".join(summary_parts)
                self._checkpoint_result = result
                self.phase = Phase.CONCURRENT
                self.generation += 1
                log.info(
                    "Checkpoint complete: generation=%d, summary=%d chars",
                    self.generation,
                    len(self.checkpoint_summary),
                )
            else:
                log.warning("Checkpoint summarization returned empty result")
                self.phase = Phase.NORMAL
        except Exception as err:
            log.error("Checkpoint summarization failed: %s", err)
            self.phase = Phase.NORMAL
            self.checkpoint_summary = None

    def wait_for_checkpoint(self, timeout=30.0):
        """Wait for a pending checkpoint to complete.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if checkpoint completed successfully.
        """
        if self._checkpoint_thread is None:
            return self.phase == Phase.CONCURRENT

        self._checkpoint_thread.join(timeout=timeout)
        if self._checkpoint_thread.is_alive():
            log.warning("Checkpoint timed out after %.1f seconds", timeout)
            return False

        self._checkpoint_thread = None
        return self.phase == Phase.CONCURRENT

    def complete_swap(self):
        """Complete the buffer swap.

        Returns the pre-computed summarized messages to replace done_messages.

        Returns:
            List of summarized messages, or empty list on error.
        """
        if self.phase != Phase.CONCURRENT or self._checkpoint_result is None:
            log.error(
                "complete_swap called in invalid state: phase=%s, has_result=%s",
                self.phase.value,
                self._checkpoint_result is not None,
            )
            return []

        result = self._checkpoint_result
        log.info(
            "Swap complete: generation=%d, swapped %d → %d messages",
            self.generation,
            self.checkpoint_done_messages_len,
            len(result),
        )

        # Reset for next cycle
        self.phase = Phase.NORMAL
        self.checkpoint_summary = None
        self.checkpoint_done_messages_len = 0
        self._checkpoint_messages_snapshot = None
        self._checkpoint_result = None

        return result

    def reset(self):
        """Reset all state. Called on error or session end."""
        if self._checkpoint_thread is not None:
            self._checkpoint_thread.join(timeout=5.0)
            self._checkpoint_thread = None
        self.phase = Phase.NORMAL
        self.checkpoint_summary = None
        self.checkpoint_done_messages_len = 0
        self._checkpoint_messages_snapshot = None
        self._checkpoint_result = None
        # Don't reset generation — it tracks lifetime compaction count
