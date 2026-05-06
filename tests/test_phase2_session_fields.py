"""
Tests for Phase 2 session fields: files_in_scope and session_summary
(KB-2026-030 Step 6).

Covers _files_changed(), _generate_summary(), and relay() integration.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch

from aider.relay.session import MTARPSession
from scripts.relay_loop import _files_changed, _generate_summary
from tests.helpers import MockProvider, exhausted_turn, success_turn


def _session(diff_since="abc1234", git_head="def5678"):
    s = MTARPSession()
    s.git_diff_since = diff_since
    s.git_head = git_head
    s.task_description = "add OAuth"
    return s


def _git_repo(diff_output="src/foo.py\nsrc/bar.py\n"):
    repo = MagicMock()
    repo.repo.git.diff.return_value = diff_output
    repo.diff_commits.return_value = "diff --git a/src/foo.py..."
    return repo


# ── _files_changed ────────────────────────────────────────────────────────────


class TestFilesChanged:
    def test_returns_list_from_git_diff(self):
        result = _files_changed(_session(), _git_repo("src/foo.py\nsrc/bar.py\n"))
        assert result == ["src/foo.py", "src/bar.py"]

    def test_strips_blank_lines(self):
        result = _files_changed(_session(), _git_repo("src/foo.py\n\nsrc/bar.py\n"))
        assert result == ["src/foo.py", "src/bar.py"]

    def test_returns_empty_when_no_git_repo(self):
        assert _files_changed(_session(), None) == []

    def test_returns_empty_when_no_diff_since(self):
        assert _files_changed(_session(diff_since=""), _git_repo()) == []

    def test_returns_empty_when_no_git_head(self):
        assert _files_changed(_session(git_head=""), _git_repo()) == []

    def test_returns_empty_on_git_exception(self):
        git_repo = _git_repo()
        git_repo.repo.git.diff.side_effect = Exception("git error")
        assert _files_changed(_session(), git_repo) == []

    def test_passes_correct_shas_to_git(self):
        git_repo = _git_repo()
        _files_changed(_session(diff_since="aaa111", git_head="bbb222"), git_repo)
        git_repo.repo.git.diff.assert_called_once_with("--name-only", "aaa111", "bbb222")


# ── _generate_summary ─────────────────────────────────────────────────────────


class TestGenerateSummary:
    def _mock_litellm(self, text):
        response = MagicMock()
        response.choices[0].message.content = text
        return response

    def test_returns_summary_string(self):
        with patch("litellm.completion", return_value=self._mock_litellm("  Added OAuth.  ")):
            result = _generate_summary("add OAuth", "diff content")
        assert result == "Added OAuth."

    def test_returns_empty_when_diff_is_empty(self):
        result = _generate_summary("add OAuth", "")
        assert result == ""

    def test_returns_empty_when_diff_is_whitespace(self):
        result = _generate_summary("add OAuth", "   \n  ")
        assert result == ""

    def test_returns_empty_on_litellm_exception(self):
        with patch("litellm.completion", side_effect=Exception("no API key")):
            result = _generate_summary("add OAuth", "diff content")
        assert result == ""

    def test_truncates_long_diff(self):
        long_diff = "x" * 10_000
        captured = {}

        def capture(**kwargs):
            captured["messages"] = kwargs["messages"]
            return self._mock_litellm("summary")

        with patch("litellm.completion", side_effect=capture):
            _generate_summary("task", long_diff)

        content = captured["messages"][0]["content"]
        assert len(content) < len(long_diff) + 500

    def test_uses_haiku_by_default(self):
        calls = []

        def capture(**kwargs):
            calls.append(kwargs)
            return self._mock_litellm("summary")

        with patch("litellm.completion", side_effect=capture):
            _generate_summary("task", "diff")

        assert calls[0]["model"] == "claude-haiku-4-5-20251001"


# ── relay() integration ───────────────────────────────────────────────────────


class TestRelayPhase2Fields:
    def _run_relay(self, tmp_path):
        from scripts.relay_loop import relay

        primary = MockProvider([exhausted_turn()], session_id="p-session")
        fallback = MockProvider([success_turn()], session_id="f-session")

        with (
            patch("aider.relay.loop.make_provider") as mock_make,
            patch("aider.relay.loop._files_changed", return_value=["src/auth.py"]),
            patch("aider.relay.loop._generate_summary", return_value="Added OAuth login support."),
            patch("builtins.input", side_effect=EOFError()),
        ):
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            asyncio.run(relay("add OAuth", "claude", "codex", session_dir=str(tmp_path)))

        return json.loads((tmp_path / "session.json").read_text())

    def test_files_in_scope_written_to_session_json(self, tmp_path):
        data = self._run_relay(tmp_path)
        assert data["files_in_scope"] == ["src/auth.py"]

    def test_session_summary_written_to_session_json(self, tmp_path):
        data = self._run_relay(tmp_path)
        assert data["session_summary"] == "Added OAuth login support."

    def test_files_in_scope_empty_list_when_helper_returns_empty(self, tmp_path):
        from scripts.relay_loop import relay

        primary = MockProvider([exhausted_turn()], session_id="p")
        fallback = MockProvider([success_turn()], session_id="f")

        with (
            patch("aider.relay.loop.make_provider") as mock_make,
            patch("aider.relay.loop._files_changed", return_value=[]),
            patch("aider.relay.loop._generate_summary", return_value=""),
            patch("builtins.input", side_effect=EOFError()),
        ):
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            asyncio.run(relay("task", "claude", "codex", session_dir=str(tmp_path)))

        data = json.loads((tmp_path / "session.json").read_text())
        assert data["files_in_scope"] == []
        assert data["session_summary"] == ""
