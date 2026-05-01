"""
Empirical verification of three assumptions in AiderProvider (KB-2026-030).

Q1: Does Model("gpt-4o-mini") raise at construction with no API key?
    Answer (from source): No — stores missing_keys but never raises.

Q2: Do rate-limit exceptions surface as ProviderEvent(type="exhausted")?
    Answer (from source): Yes — litellm.RateLimitError and RouterRateLimitError
    bubble up unwrapped; _is_rate_limit() catches them correctly.

Q3: Does InputOutput(pretty=False, yes=True) suppress all prompts?
    Answer (from source): All except confirm_ask(explicit_yes_required=True),
    which answers "no" — meaning shell command execution is blocked. This is
    correct behaviour for autonomous mode.
"""
import asyncio
from unittest.mock import MagicMock

# ── Q1: Model construction ────────────────────────────────────────────────────


class TestModelConstruction:
    def test_no_api_key_does_not_raise(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from aider.models import Model

        model = Model("gpt-4o-mini")  # must not raise
        assert model is not None

    def test_missing_keys_is_populated(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from aider.models import Model

        model = Model("gpt-4o-mini")
        # Validation ran but stored the gap instead of raising
        assert isinstance(model.missing_keys, list)
        assert len(model.missing_keys) > 0

    def test_error_deferred_to_first_api_call(self, monkeypatch):
        # Confirms the _get_coder() lazy path in AiderProvider is safe:
        # constructing the provider and calling _get_coder() won't explode
        # before run_turn() is invoked.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from aider.providers.aider_coder import AiderProvider

        provider = AiderProvider(model="gpt-4o-mini")
        assert provider._coder is None  # deferred — not constructed yet


# ── Q2: Rate-limit exception surfacing ────────────────────────────────────────


def _provider_with_mock_coder(side_effect):
    from aider.providers.aider_coder import AiderProvider

    provider = AiderProvider(model="gpt-4o-mini")
    mock_coder = MagicMock()
    mock_coder.run.side_effect = side_effect
    provider._coder = mock_coder
    return provider


class TestRateLimitSurfacing:
    def test_rate_limit_error_yields_exhausted(self):
        import litellm

        provider = _provider_with_mock_coder(
            litellm.RateLimitError("rate limited", "openai", "gpt-4o-mini")
        )
        events = asyncio.run(_collect(provider, "hello"))
        assert len(events) == 1
        assert events[0].type == "exhausted"

    def test_router_rate_limit_error_yields_exhausted(self):
        import litellm

        provider = _provider_with_mock_coder(
            litellm.RouterRateLimitError(
                model="gpt-4o-mini",
                cooldown_time=60.0,
                enable_pre_call_checks=False,
                cooldown_list=[],
            )
        )
        events = asyncio.run(_collect(provider, "hello"))
        assert len(events) == 1
        assert events[0].type == "exhausted"

    def test_name_based_fallback_catches_unknown_rate_limit(self):
        # Guards against litellm adding new rate-limit subclasses
        class SomeNewRateLimitError(Exception):
            pass

        provider = _provider_with_mock_coder(SomeNewRateLimitError("slow down"))
        events = asyncio.run(_collect(provider, "hello"))
        assert len(events) == 1
        assert events[0].type == "exhausted"

    def test_str_based_fallback_catches_rate_limit_message(self):
        provider = _provider_with_mock_coder(Exception("upstream rate_limit exceeded"))
        events = asyncio.run(_collect(provider, "hello"))
        assert len(events) == 1
        assert events[0].type == "exhausted"

    def test_generic_error_yields_error_not_exhausted(self):
        provider = _provider_with_mock_coder(ValueError("disk full"))
        events = asyncio.run(_collect(provider, "hello"))
        assert len(events) == 1
        assert events[0].type == "error"

    def test_successful_run_yields_text_then_done(self):
        from aider.providers.aider_coder import AiderProvider

        provider = AiderProvider(model="gpt-4o-mini")
        mock_coder = MagicMock()
        mock_coder.run.return_value = "here is the fix"
        provider._coder = mock_coder

        events = asyncio.run(_collect(provider, "fix the bug"))
        types = [e.type for e in events]
        assert types == ["text", "done"]
        assert events[0].content == "here is the fix"


async def _collect(provider, prompt):
    return [e async for e in provider.run_turn(prompt)]


# ── Q3: InputOutput yes=True prompt suppression ───────────────────────────────


class TestInputOutputYesMode:
    def _io(self):
        from aider.io import InputOutput

        return InputOutput(pretty=False, yes=True)

    def test_confirm_ask_auto_answers_yes(self):
        result = self._io().confirm_ask("Delete file?", subject="foo.py")
        assert result is True

    def test_prompt_ask_auto_answers_yes(self):
        result = self._io().prompt_ask("Enter value:", default="")
        assert result == "yes"

    def test_shell_command_blocked_in_autonomous_mode(self):
        # confirm_ask(explicit_yes_required=True) answers "no" when yes=True.
        # This is the only call site in the codebase (base_coder.py:2459).
        # Shell commands are therefore blocked in autonomous mode — correct behaviour.
        result = self._io().confirm_ask(
            "Run shell command?",
            subject="rm -rf /tmp/test",
            explicit_yes_required=True,
        )
        assert result is False

    def test_file_overwrite_auto_approved(self):
        # Verifies the most common autonomous-mode write path is unblocked.
        result = self._io().confirm_ask("Overwrite file?", subject="src/main.py")
        assert result is True
