"""
Tests for relay infrastructure gaps (KB-2026-039/040/042).

Covers: interrupt sentinel, turn timeout, handoff envelope validation,
merge-readiness review prompt, and timeout treated as exhaustion.
"""
import asyncio
from unittest.mock import patch

from aider.providers.base import ProviderEvent
from aider.relay.session import MTARPSession
from scripts.relay_loop import _check_interrupt, relay, run_turn
from tests.helpers import MockProvider, success_turn

# ── _check_interrupt ──────────────────────────────────────────────────────────


class TestCheckInterrupt:
    def test_returns_false_when_no_sentinel(self, tmp_path):
        assert _check_interrupt(str(tmp_path)) is False

    def test_returns_true_when_sentinel_exists(self, tmp_path):
        (tmp_path / "interrupt").touch()
        assert _check_interrupt(str(tmp_path)) is True

    def test_removes_sentinel_after_detecting(self, tmp_path):
        (tmp_path / "interrupt").touch()
        _check_interrupt(str(tmp_path))
        assert not (tmp_path / "interrupt").exists()

    def test_idempotent_after_first_check(self, tmp_path):
        (tmp_path / "interrupt").touch()
        _check_interrupt(str(tmp_path))
        assert _check_interrupt(str(tmp_path)) is False


# ── Interrupt sentinel stops relay ────────────────────────────────────────────


class TestInterruptSentinelStopsRelay:
    def test_relay_stops_when_sentinel_present_before_second_turn(self, tmp_path):
        """Sentinel placed after first turn completes → relay stops before second turn."""
        call_count = 0

        class SentinelPlacingProvider(MockProvider):
            async def run_turn(self, prompt):
                nonlocal call_count
                call_count += 1
                # Place sentinel after first turn so relay reads it before turn 2
                if call_count == 1:
                    (tmp_path / "interrupt").touch()
                async for e in super().run_turn(prompt):
                    yield e

        primary = SentinelPlacingProvider([success_turn(), success_turn(), success_turn()])
        fallback = MockProvider([success_turn()])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(
                    relay(
                        "test task",
                        "claude",
                        "codex",
                        session_dir=str(tmp_path),
                        autonomous=True,
                        max_turns=10,
                    )
                )

        assert call_count == 1


# ── run_turn timeout ──────────────────────────────────────────────────────────


class TestRunTurnTimeout:
    def test_returns_timeout_when_provider_hangs(self):
        class HangingProvider(MockProvider):
            async def run_turn(self, prompt):
                await asyncio.sleep(10)  # simulate stuck provider
                yield ProviderEvent(type="done")

        provider = HangingProvider([])
        result = asyncio.run(run_turn(provider, "prompt", "TEST", turn_timeout=1))
        assert result == "timeout"

    def test_no_timeout_when_turn_timeout_zero(self):
        provider = MockProvider([success_turn()])
        result = asyncio.run(run_turn(provider, "prompt", "TEST", turn_timeout=0))
        assert result is None

    def test_fast_turn_completes_within_timeout(self):
        provider = MockProvider([success_turn()])
        result = asyncio.run(run_turn(provider, "prompt", "TEST", turn_timeout=5))
        assert result is None


# ── timeout treated as exhaustion in relay ────────────────────────────────────


class TestTimeoutTreatedAsExhaustion:
    def test_relay_switches_provider_on_timeout(self, tmp_path):
        fallback_called = []

        class HangingProvider(MockProvider):
            async def run_turn(self, prompt):
                await asyncio.sleep(10)
                yield ProviderEvent(type="done")

        class TrackingProvider(MockProvider):
            async def run_turn(self, prompt):
                fallback_called.append(prompt)
                async for e in super().run_turn(prompt):
                    yield e

        primary = HangingProvider([])
        fallback = TrackingProvider([success_turn()])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(
                    relay(
                        "test task",
                        "claude",
                        "codex",
                        session_dir=str(tmp_path),
                        turn_timeout=1,
                    )
                )

        assert fallback_called, "fallback was never called after primary timed out"

    def test_session_json_written_on_timeout(self, tmp_path):
        class HangingProvider(MockProvider):
            async def run_turn(self, prompt):
                await asyncio.sleep(10)
                yield ProviderEvent(type="done")

        primary = HangingProvider([])
        fallback = MockProvider([success_turn()])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(
                    relay(
                        "test task",
                        "claude",
                        "codex",
                        session_dir=str(tmp_path),
                        turn_timeout=1,
                    )
                )

        assert (tmp_path / "session.json").exists()

    def test_session_json_handoff_reason_is_timeout(self, tmp_path):
        import json

        class HangingProvider(MockProvider):
            async def run_turn(self, prompt):
                await asyncio.sleep(10)
                yield ProviderEvent(type="done")

        primary = HangingProvider([])
        fallback = MockProvider([success_turn()])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(
                    relay(
                        "test task",
                        "claude",
                        "codex",
                        session_dir=str(tmp_path),
                        turn_timeout=1,
                    )
                )

        data = json.loads((tmp_path / "session.json").read_text())
        assert data["handoff"]["reason"] == "timeout"


# ── MTARPSession.validate_handoff() ──────────────────────────────────────────


class TestValidateHandoff:
    def test_no_warnings_when_all_fields_populated(self):
        s = MTARPSession(
            task_description="test",
            git_head="abc123",
            files_in_scope=["src/foo.py"],
            session_summary="Added OAuth support.",
        )
        assert s.validate_handoff() == []

    def test_warns_on_empty_session_summary(self):
        s = MTARPSession(task_description="test", git_head="abc123", files_in_scope=["foo.py"])
        warnings = s.validate_handoff()
        assert any("session_summary" in w for w in warnings)

    def test_warns_on_empty_files_in_scope(self):
        s = MTARPSession(task_description="test", git_head="abc123", session_summary="Done.")
        warnings = s.validate_handoff()
        assert any("files_in_scope" in w for w in warnings)

    def test_warns_on_empty_git_head(self):
        s = MTARPSession(
            task_description="test", files_in_scope=["foo.py"], session_summary="Done."
        )
        warnings = s.validate_handoff()
        assert any("git.head" in w for w in warnings)

    def test_returns_multiple_warnings(self):
        s = MTARPSession(task_description="test")
        warnings = s.validate_handoff()
        assert len(warnings) >= 2


# ── merge-readiness review prompt ────────────────────────────────────────────


class TestMergeReviewPrompt:
    def test_merge_review_prompt_sent_on_max_turns(self, tmp_path):
        review_prompts = []

        class CapturingProvider(MockProvider):
            async def run_turn(self, prompt):
                review_prompts.append(prompt)
                async for e in super().run_turn(prompt):
                    yield e

        primary = CapturingProvider([success_turn(), success_turn()])
        fallback = MockProvider([])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            asyncio.run(
                relay(
                    "test task",
                    "claude",
                    "codex",
                    session_dir=str(tmp_path),
                    autonomous=True,
                    max_turns=1,
                    merge_review=True,
                )
            )

        assert len(review_prompts) == 2
        assert (
            "merge-readiness" in review_prompts[-1].lower()
            or "self-review" in review_prompts[-1].lower()
        )

    def test_no_extra_turn_without_merge_review_flag(self, tmp_path):
        turn_count = [0]

        class CountingProvider(MockProvider):
            async def run_turn(self, prompt):
                turn_count[0] += 1
                async for e in super().run_turn(prompt):
                    yield e

        primary = CountingProvider([success_turn()])
        fallback = MockProvider([])

        with patch("aider.relay.loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            asyncio.run(
                relay(
                    "test task",
                    "claude",
                    "codex",
                    session_dir=str(tmp_path),
                    autonomous=True,
                    max_turns=1,
                    merge_review=False,
                )
            )

        assert turn_count[0] == 1
