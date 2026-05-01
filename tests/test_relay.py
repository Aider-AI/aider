"""
Unit tests for relay_loop.py — Phase 1 validation.

Tests the relay state machine, sim-exhaust logic, handoff prompt construction,
and git_context output using mock providers. No real CLI calls.
"""
import asyncio
import subprocess
from unittest.mock import patch

from aider.providers.base import ProviderEvent
from scripts.relay_loop import git_context, handoff_prompt, relay, run_turn
from tests.helpers import MockProvider, error_turn, exhausted_turn, success_turn

# ── git_context ───────────────────────────────────────────────────────────────


class TestGitContext:
    def test_returns_string_with_headings(self):
        result = git_context()
        assert "Recent git history:" in result
        assert "Current uncommitted changes:" in result

    def test_has_git_history_or_fallback(self):
        result = git_context()
        # Either real git history or the fallback string
        assert "no git history" in result or len(result.split("\n")) > 3

    def test_graceful_when_git_not_on_path(self):
        with patch("subprocess.check_output", side_effect=OSError("git not found")):
            # FileNotFoundError (OSError subclass) when git binary is absent
            result = git_context()
        assert "Recent git history:" in result
        assert "no git history" in result
        assert "Current uncommitted changes:" in result

    def test_graceful_when_git_command_fails(self):
        with patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(128, "git")
        ):
            result = git_context()
        assert "no git history" in result


# ── git_context with GitRepo ──────────────────────────────────────────────────


class TestGitContextWithRepo:
    def test_falls_back_gracefully_when_git_repo_raises(self):
        class _BadRepo:
            @property
            def repo(self):
                raise RuntimeError("broken")

        result = git_context(git_repo=_BadRepo())
        # Must fall through to subprocess and still return the expected structure
        assert "Recent git history:" in result
        assert "Current uncommitted changes:" in result

    def test_uses_git_repo_when_provided(self):
        class _FakeGit:
            def log(self, *a, **kw):
                return "abc1234 fake commit"

        class _FakeInnerRepo:
            git = _FakeGit()

        class _FakeRepo:
            repo = _FakeInnerRepo()

            def get_diffs(self):
                return "diff --git a/foo.py"

        result = git_context(git_repo=_FakeRepo())
        assert "fake commit" in result
        assert "diff --git" in result


# ── handoff_prompt ────────────────────────────────────────────────────────────


class TestHandoffPrompt:
    def test_contains_task(self):
        prompt = handoff_prompt("add OAuth login")
        assert "add OAuth login" in prompt

    def test_contains_continuation_framing(self):
        prompt = handoff_prompt("any task")
        assert "continuing" in prompt.lower()
        assert "previous" in prompt.lower()

    def test_contains_git_context_headings(self):
        prompt = handoff_prompt("any task")
        assert "Recent git history" in prompt
        assert "Current uncommitted changes" in prompt

    def test_task_section_present(self):
        prompt = handoff_prompt("fix the bug")
        assert "## Task" in prompt
        assert "fix the bug" in prompt


# ── run_turn ──────────────────────────────────────────────────────────────────


class TestRunTurn:
    def test_returns_none_on_success(self, capsys):
        provider = MockProvider([success_turn("hello")])
        result = asyncio.run(run_turn(provider, "prompt", "TEST"))
        assert result is None
        assert "hello" in capsys.readouterr().out

    def test_returns_exhausted_on_exhaustion(self, capsys):
        provider = MockProvider([exhausted_turn(reset_at="2026-05-01T00:00:00Z")])
        result = asyncio.run(run_turn(provider, "prompt", "TEST"))
        assert result == "exhausted"
        out = capsys.readouterr().out
        assert "exhausted" in out.lower()
        assert "2026-05-01" in out

    def test_exhausted_without_reset_at(self, capsys):
        provider = MockProvider([exhausted_turn(reset_at=None)])
        result = asyncio.run(run_turn(provider, "prompt", "TEST"))
        assert result == "exhausted"

    def test_prints_error_but_returns_none(self, capsys):
        provider = MockProvider([error_turn("disk full")])
        result = asyncio.run(run_turn(provider, "prompt", "TEST"))
        assert result is None
        assert "disk full" in capsys.readouterr().out

    def test_prompt_passed_to_provider(self):
        provider = MockProvider([success_turn()])
        asyncio.run(run_turn(provider, "my specific prompt", "TEST"))
        assert provider.prompts_received == ["my specific prompt"]


# ── relay state machine ───────────────────────────────────────────────────────


class TestRelayStateMachine:
    """Tests for relay() using mock providers and controlled stdin."""

    def _run_relay(self, primary_turns, fallback_turns, sim_exhaust_after=0, stdin_lines=None):
        """Helper: run relay() with mock providers, optionally feeding stdin."""
        primary = MockProvider(primary_turns, session_id="primary-session")
        fallback = MockProvider(fallback_turns, session_id="fallback-session")

        with patch("scripts.relay_loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            if stdin_lines is not None:
                with patch("builtins.input", side_effect=stdin_lines + [EOFError()]):
                    asyncio.run(relay("test task", "claude", "codex", sim_exhaust_after))
            else:
                with patch("builtins.input", side_effect=EOFError()):
                    asyncio.run(relay("test task", "claude", "codex", sim_exhaust_after))
        return primary, fallback

    # ── sim_exhaust_after tests ───────────────────────────────────────────────

    def test_sim_exhaust_after_1_switches_to_fallback(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn("primary response")],
            fallback_turns=[success_turn("fallback response")],
            sim_exhaust_after=1,
        )
        out = capsys.readouterr().out
        assert "primary response" in out
        assert "fallback response" in out
        assert "Switching" in out

    def test_sim_exhaust_after_1_both_exhausted_stops(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn()],
            fallback_turns=[success_turn()],
            sim_exhaust_after=1,
        )
        out = capsys.readouterr().out
        assert "Both providers exhausted" in out

    def test_sim_exhaust_after_2_runs_two_primary_turns(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn("turn1"), success_turn("turn2")],
            fallback_turns=[success_turn("fallback")],
            sim_exhaust_after=2,
            stdin_lines=["continue"],
        )
        assert len(primary.prompts_received) == 2
        out = capsys.readouterr().out
        assert "turn1" in out
        assert "turn2" in out

    def test_sim_exhaust_resets_counter_for_fallback(self, capsys):
        """Fallback provider also gets its own turn counter starting from 0."""
        primary, fallback = self._run_relay(
            primary_turns=[success_turn("p1"), success_turn("p2")],
            fallback_turns=[success_turn("f1"), success_turn("f2")],
            sim_exhaust_after=2,
            stdin_lines=["continue"],  # feeds primary turn 2 prompt
        )
        # Primary gets 2 turns, then exhausts. Fallback gets its first turn,
        # which starts its counter at 1 < 2 — so it waits for input (EOFError breaks).
        assert len(primary.prompts_received) == 2
        assert len(fallback.prompts_received) == 1

    # ── real provider exhaustion ──────────────────────────────────────────────

    def test_real_exhaustion_triggers_switch(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[success_turn("fallback took over")],
        )
        out = capsys.readouterr().out
        assert "fallback took over" in out
        assert "Switching" in out

    def test_both_real_exhaustion_stops(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[exhausted_turn()],
        )
        out = capsys.readouterr().out
        assert "Both providers exhausted" in out

    def test_exhaustion_count_resets_correctly(self, capsys):
        """Two separate real-exhaustion events (one per provider) stops the relay."""
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[exhausted_turn()],
        )
        out = capsys.readouterr().out
        assert "Both providers exhausted" in out
        # Neither provider received a second prompt
        assert len(primary.prompts_received) == 1
        assert len(fallback.prompts_received) == 1

    # ── handoff prompt on switch ──────────────────────────────────────────────

    def test_fallback_receives_handoff_prompt(self):
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[success_turn()],
        )
        assert len(fallback.prompts_received) == 1
        prompt = fallback.prompts_received[0]
        assert "continuing" in prompt.lower()
        assert "test task" in prompt

    def test_fallback_handoff_prompt_contains_task(self):
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[success_turn()],
        )
        prompt = fallback.prompts_received[0]
        assert "test task" in prompt

    def test_initial_prompt_is_task_not_handoff(self):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn()],
            fallback_turns=[],
        )
        assert primary.prompts_received[0] == "test task"

    # ── multi-turn (user follow-up) ───────────────────────────────────────────

    def test_multi_turn_second_prompt_passed_to_provider(self):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn(), success_turn()],
            fallback_turns=[],
            stdin_lines=["follow up question"],
        )
        assert primary.prompts_received[0] == "test task"
        assert primary.prompts_received[1] == "follow up question"

    def test_empty_input_stops_relay(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[success_turn()],
            fallback_turns=[],
            stdin_lines=[""],  # empty input → break
        )
        assert len(primary.prompts_received) == 1

    def test_eoferror_stops_relay_gracefully(self):
        # EOFError on first input call stops relay without exception
        primary, fallback = self._run_relay(
            primary_turns=[success_turn()],
            fallback_turns=[],
            stdin_lines=None,  # triggers EOFError immediately
        )
        assert len(primary.prompts_received) == 1

    # ── autonomous mode ───────────────────────────────────────────────────────

    def test_autonomous_runs_without_user_input(self, capsys):
        primary, fallback = self._run_relay_autonomous(
            primary_turns=[success_turn("auto1"), success_turn("auto2")],
            fallback_turns=[],
            max_turns=2,
        )
        out = capsys.readouterr().out
        assert "auto1" in out
        assert "auto2" in out
        assert "max turns" in out.lower()

    def test_autonomous_continuation_prompt_sent(self):
        primary, _ = self._run_relay_autonomous(
            primary_turns=[success_turn("a"), success_turn("b")],
            fallback_turns=[],
            max_turns=2,
        )
        assert len(primary.prompts_received) == 2
        assert "continue" in primary.prompts_received[1].lower()

    def test_autonomous_switches_on_exhaustion(self, capsys):
        primary, fallback = self._run_relay_autonomous(
            primary_turns=[exhausted_turn()],
            fallback_turns=[success_turn("fallback auto")],
            max_turns=1,
        )
        out = capsys.readouterr().out
        assert "fallback auto" in out

    def _run_relay_autonomous(self, primary_turns, fallback_turns, max_turns=0):
        primary = MockProvider(primary_turns, session_id="primary-session")
        fallback = MockProvider(fallback_turns, session_id="fallback-session")
        with patch("scripts.relay_loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            asyncio.run(
                relay(
                    "test task",
                    "claude",
                    "codex",
                    sim_exhaust_after=0,
                    autonomous=True,
                    max_turns=max_turns,
                )
            )
        return primary, fallback

    # ── provider cycling ──────────────────────────────────────────────────────

    def test_both_exhausted_stops_with_set_tracking(self, capsys):
        primary, fallback = self._run_relay(
            primary_turns=[exhausted_turn()],
            fallback_turns=[exhausted_turn()],
        )
        out = capsys.readouterr().out
        assert "Both providers exhausted" in out

    # ── provider tier ─────────────────────────────────────────────────────────

    def test_mock_provider_tier_is_agentic_cli(self):
        provider = MockProvider([])
        assert provider.tier == "agentic_cli"


# ── task-file support ────────────────────────────────────────────────────────


class TestTaskFile:
    def test_relay_uses_task_file_content(self, tmp_path):
        task_file = tmp_path / "TASK.md"
        task_file.write_text("build the OAuth feature")

        primary = MockProvider([success_turn()], session_id="p")
        with patch("scripts.relay_loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(relay(task_file.read_text().strip(), "claude", "codex"))
        assert primary.prompts_received[0] == "build the OAuth feature"


# ── AiderProvider unit ────────────────────────────────────────────────────────


class TestAiderProvider:
    def test_tier_is_completion_api(self):
        from aider.providers.aider_coder import AiderProvider

        p = AiderProvider("gpt-4o-mini")
        assert p.tier == "completion_api"

    def test_current_session_id_is_none(self):
        from aider.providers.aider_coder import AiderProvider

        p = AiderProvider("gpt-4o-mini")
        assert p.current_session_id is None

    def test_is_rate_limit_detects_by_name(self):
        from aider.providers.aider_coder import _is_rate_limit

        class FakeRateLimitError(Exception):
            pass

        assert _is_rate_limit(FakeRateLimitError("RateLimitError hit"))

    def test_is_rate_limit_detects_by_message(self):
        from aider.providers.aider_coder import _is_rate_limit

        assert _is_rate_limit(Exception("rate_limit exceeded"))

    def test_is_rate_limit_false_for_generic(self):
        from aider.providers.aider_coder import _is_rate_limit

        assert not _is_rate_limit(ValueError("something else"))


# ── ProviderEvent dataclass ───────────────────────────────────────────────────


class TestProviderEvent:
    def test_defaults(self):
        event = ProviderEvent(type="text")
        assert event.content == ""
        assert event.reset_at is None
        assert event.session_id is None

    def test_exhausted_with_reset(self):
        event = ProviderEvent(type="exhausted", reset_at="2026-05-01T00:00:00Z")
        assert event.reset_at == "2026-05-01T00:00:00Z"

    def test_text_event(self):
        event = ProviderEvent(type="text", content="hello world")
        assert event.content == "hello world"
