"""
Tests for RepoMap handoff context (KB-2026-028 / Step 5).

Verifies that _build_repomap_context() and the RepoMap section in
handoff_prompt() behave correctly under both happy-path and failure conditions.
"""
from unittest.mock import MagicMock, patch

from aider.relay.session import MTARPSession
from scripts.relay_loop import _build_repomap_context, handoff_prompt


def _session(diff_since="abc1234", git_head="def5678"):
    s = MTARPSession()
    s.git_diff_since = diff_since
    s.git_head = git_head
    s.task_description = "add OAuth"
    return s


def _git_repo(tracked=("src/foo.py", "src/bar.py"), diff_output="src/foo.py\n"):
    repo = MagicMock()
    repo.get_tracked_files.return_value = list(tracked)
    repo.repo.git.diff.return_value = diff_output
    return repo


# ── _build_repomap_context ────────────────────────────────────────────────────


class TestBuildRepomapContext:
    def _run(self, session, git_repo, map_output="src/foo.py:\n│ def foo()\n"):
        mock_rm = MagicMock()
        mock_rm.get_repo_map.return_value = map_output
        with (
            patch("aider.repomap.RepoMap", return_value=mock_rm),
            patch("aider.models.Model"),
            patch("aider.io.InputOutput"),
        ):
            return _build_repomap_context(session, git_repo), mock_rm

    def test_returns_map_string_on_success(self):
        result, _ = self._run(_session(), _git_repo())
        assert "foo" in result

    def test_passes_changed_files_as_chat_files(self):
        result, mock_rm = self._run(_session(), _git_repo(diff_output="src/foo.py\n"))
        call_kwargs = mock_rm.get_repo_map.call_args
        assert "src/foo.py" in call_kwargs.kwargs.get(
            "chat_files", call_kwargs.args[0] if call_kwargs.args else []
        )

    def test_passes_all_tracked_files_as_other_files(self):
        result, mock_rm = self._run(_session(), _git_repo(tracked=["src/foo.py", "src/bar.py"]))
        call_args = mock_rm.get_repo_map.call_args
        other = call_args.kwargs.get(
            "other_files", call_args.args[1] if len(call_args.args) > 1 else []
        )
        assert "src/bar.py" in other

    def test_returns_empty_string_when_no_tracked_files(self):
        result, _ = self._run(_session(), _git_repo(tracked=[]))
        assert result == ""

    def test_returns_empty_string_when_repomap_returns_none(self):
        result, _ = self._run(_session(), _git_repo(), map_output=None)
        assert result == ""

    def test_returns_empty_string_on_repomap_exception(self):
        git_repo = _git_repo()
        with patch("aider.repomap.RepoMap", side_effect=RuntimeError("tree-sitter unavailable")):
            result = _build_repomap_context(_session(), git_repo)
        assert result == ""

    def test_returns_empty_string_on_git_diff_exception(self):
        git_repo = _git_repo()
        git_repo.repo.git.diff.side_effect = Exception("git error")
        mock_rm = MagicMock()
        mock_rm.get_repo_map.return_value = "some map"
        with (
            patch("aider.repomap.RepoMap", return_value=mock_rm),
            patch("aider.models.Model"),
            patch("aider.io.InputOutput"),
        ):
            # Should still succeed — changed files will be empty, all_files used
            result = _build_repomap_context(_session(), git_repo)
        assert result == "some map"

    def test_handles_empty_diff_since(self):
        session = _session(diff_since="", git_head="def5678")
        mock_rm = MagicMock()
        mock_rm.get_repo_map.return_value = "map"
        with (
            patch("aider.repomap.RepoMap", return_value=mock_rm),
            patch("aider.models.Model"),
            patch("aider.io.InputOutput"),
        ):
            result = _build_repomap_context(session, _git_repo())
        # No diff attempted when diff_since is empty; still returns map
        assert result == "map"


# ── handoff_prompt with RepoMap ───────────────────────────────────────────────


class TestHandoffPromptRepomap:
    def test_includes_repomap_section_when_available(self):
        session = _session()
        git_repo = _git_repo()
        with patch(
            "aider.relay.loop._build_repomap_context",
            return_value="src/foo.py:\n│ def foo()\n",
        ):
            prompt = handoff_prompt("add OAuth", session=session, git_repo=git_repo)
        assert "## Repository map" in prompt
        assert "def foo" in prompt

    def test_repomap_section_absent_when_empty(self):
        session = _session()
        git_repo = _git_repo()
        with patch("aider.relay.loop._build_repomap_context", return_value=""):
            prompt = handoff_prompt("add OAuth", session=session, git_repo=git_repo)
        assert "## Repository map" not in prompt

    def test_repomap_section_absent_without_git_repo(self):
        # Patch subprocess so git_context returns a clean string regardless of
        # the working tree state (avoids false positives from uncommitted diffs).
        with patch("subprocess.check_output", return_value="(clean)"):
            prompt = handoff_prompt("add OAuth", session=_session(), git_repo=None)
        assert "## Repository map" not in prompt

    def test_repomap_section_absent_without_session(self):
        prompt = handoff_prompt("add OAuth", session=None, git_repo=_git_repo())
        assert "## Repository map" not in prompt

    def test_repomap_appears_before_diff_section(self):
        session = _session()
        git_repo = _git_repo()
        with patch(
            "aider.relay.loop._build_repomap_context",
            return_value="src/foo.py:\n│ def foo()\n",
        ):
            prompt = handoff_prompt("add OAuth", session=session, git_repo=git_repo)
        map_pos = prompt.index("## Repository map")
        # Either diff heading variant
        diff_heading = (
            "## What was done" if "## What was done" in prompt else "## What has been done"
        )
        diff_pos = prompt.index(diff_heading)
        assert map_pos < diff_pos

    def test_task_still_present_with_repomap(self):
        session = _session()
        with patch("aider.relay.loop._build_repomap_context", return_value="map content"):
            prompt = handoff_prompt("add OAuth login", session=session, git_repo=_git_repo())
        assert "add OAuth login" in prompt

    def test_mtarp_note_still_present_with_repomap(self):
        session = _session()
        with patch("aider.relay.loop._build_repomap_context", return_value="map content"):
            prompt = handoff_prompt("add OAuth", session=session, git_repo=_git_repo())
        assert "session.json" in prompt
