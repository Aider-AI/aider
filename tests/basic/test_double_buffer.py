"""Tests for double-buffer context management."""

import threading
from unittest.mock import MagicMock

import pytest

from aider.double_buffer import DoubleBufferManager, Phase


class TestPhaseTransitions:
    """Test the state machine transitions."""

    def test_starts_in_normal_phase(self):
        mgr = DoubleBufferManager()
        assert mgr.phase == Phase.NORMAL
        assert mgr.checkpoint_summary is None
        assert mgr.generation == 0

    def test_invalid_thresholds(self):
        with pytest.raises(ValueError):
            DoubleBufferManager(checkpoint_threshold=0.90, swap_threshold=0.60)
        with pytest.raises(ValueError):
            DoubleBufferManager(checkpoint_threshold=0, swap_threshold=0.85)
        with pytest.raises(ValueError):
            DoubleBufferManager(checkpoint_threshold=0.60, swap_threshold=1.1)

    def test_begin_checkpoint_transitions(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()

        # Use an event to block the summarizer so we can observe CHECKPOINT_PENDING
        gate = threading.Event()

        def slow_summarize(msgs):
            gate.wait(timeout=5.0)
            return [
                {"role": "user", "content": "Summary of conversation"},
                {"role": "assistant", "content": "Ok."},
            ]

        mock_summarizer.summarize.side_effect = slow_summarize
        mgr.begin_checkpoint(
            [{"role": "user", "content": "hello"}],
            mock_summarizer,
        )
        assert mgr.phase == Phase.CHECKPOINT_PENDING
        gate.set()
        mgr.wait_for_checkpoint()
        assert mgr.phase == Phase.CONCURRENT
        assert mgr.generation == 1
        assert mgr.checkpoint_summary is not None

    def test_complete_swap_returns_summary(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()
        summarized = [
            {"role": "user", "content": "Summary"},
            {"role": "assistant", "content": "Ok."},
        ]
        mock_summarizer.summarize.return_value = summarized
        mgr.begin_checkpoint(
            [{"role": "user", "content": "hello"}],
            mock_summarizer,
        )
        mgr.wait_for_checkpoint()
        result = mgr.complete_swap()
        assert result == summarized
        assert mgr.phase == Phase.NORMAL
        assert mgr.checkpoint_summary is None

    def test_full_lifecycle(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()

        # Use an event to block the summarizer so we can observe CHECKPOINT_PENDING
        gate = threading.Event()

        def slow_summarize(msgs):
            gate.wait(timeout=5.0)
            return [
                {"role": "user", "content": "Summary"},
                {"role": "assistant", "content": "Ok."},
            ]

        mock_summarizer.summarize.side_effect = slow_summarize

        assert mgr.phase == Phase.NORMAL
        mgr.begin_checkpoint([{"role": "user", "content": "test"}], mock_summarizer)
        assert mgr.phase == Phase.CHECKPOINT_PENDING
        gate.set()
        mgr.wait_for_checkpoint()
        assert mgr.phase == Phase.CONCURRENT
        assert mgr.generation == 1
        result = mgr.complete_swap()
        assert len(result) == 2
        assert mgr.phase == Phase.NORMAL
        assert mgr.generation == 1  # preserved

    def test_multiple_generations(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = [
            {"role": "user", "content": "Summary"},
            {"role": "assistant", "content": "Ok."},
        ]

        for i in range(3):
            mgr.begin_checkpoint([{"role": "user", "content": f"gen {i}"}], mock_summarizer)
            mgr.wait_for_checkpoint()
            mgr.complete_swap()

        assert mgr.generation == 3


class TestThresholdChecks:
    """Test shouldCheckpoint and shouldSwap."""

    def test_should_checkpoint_normal_phase(self):
        mgr = DoubleBufferManager(checkpoint_threshold=0.60, swap_threshold=0.85)
        # 600 of 1000 = 60%, should checkpoint
        assert mgr.should_checkpoint(600, 1000) is True

    def test_should_not_checkpoint_below_threshold(self):
        mgr = DoubleBufferManager(checkpoint_threshold=0.60)
        assert mgr.should_checkpoint(500, 1000) is False

    def test_should_not_checkpoint_wrong_phase(self):
        mgr = DoubleBufferManager(checkpoint_threshold=0.60)
        mgr.phase = Phase.CHECKPOINT_PENDING
        assert mgr.should_checkpoint(700, 1000) is False

    def test_should_swap_concurrent_phase(self):
        mgr = DoubleBufferManager(checkpoint_threshold=0.60, swap_threshold=0.85)
        mgr.phase = Phase.CONCURRENT
        mgr.checkpoint_summary = "test summary"
        assert mgr.should_swap(850, 1000) is True

    def test_should_not_swap_wrong_phase(self):
        mgr = DoubleBufferManager(swap_threshold=0.85)
        assert mgr.should_swap(900, 1000) is False

    def test_should_not_swap_no_summary(self):
        mgr = DoubleBufferManager(swap_threshold=0.85)
        mgr.phase = Phase.CONCURRENT
        mgr.checkpoint_summary = None
        assert mgr.should_swap(900, 1000) is False

    def test_should_not_checkpoint_zero_max(self):
        mgr = DoubleBufferManager()
        assert mgr.should_checkpoint(500, 0) is False

    def test_should_not_swap_zero_max(self):
        mgr = DoubleBufferManager()
        mgr.phase = Phase.CONCURRENT
        mgr.checkpoint_summary = "test"
        assert mgr.should_swap(500, 0) is False


class TestErrorHandling:
    """Test failure modes."""

    def test_summarization_failure_resets_to_normal(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.side_effect = ValueError("Model failed")

        mgr.begin_checkpoint([{"role": "user", "content": "test"}], mock_summarizer)
        mgr.wait_for_checkpoint()

        assert mgr.phase == Phase.NORMAL
        assert mgr.checkpoint_summary is None

    def test_empty_summarization_resets_to_normal(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = None

        mgr.begin_checkpoint([{"role": "user", "content": "test"}], mock_summarizer)
        mgr.wait_for_checkpoint()

        assert mgr.phase == Phase.NORMAL

    def test_complete_swap_invalid_state(self):
        mgr = DoubleBufferManager()
        result = mgr.complete_swap()
        assert result == []

    def test_reset_clears_everything(self):
        mgr = DoubleBufferManager()
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = [
            {"role": "user", "content": "Summary"},
            {"role": "assistant", "content": "Ok."},
        ]
        mgr.begin_checkpoint([{"role": "user", "content": "test"}], mock_summarizer)
        mgr.wait_for_checkpoint()
        mgr.reset()
        assert mgr.phase == Phase.NORMAL
        assert mgr.checkpoint_summary is None
        assert mgr.generation == 1  # preserved across reset
