"""
TDD tests for MTARP Phase 1 session envelope.

These tests define the contract for MTARPSession and the relay's session-writing
behaviour. They are written BEFORE the implementation — all should fail until
aider/relay/session.py exists and relay_loop.py is updated.

KB references: KB-2026-021, KB-2026-022, KB-2026-007
"""
import asyncio
import json
import uuid
from unittest.mock import patch

from tests.helpers import MockProvider, exhausted_turn, success_turn

# ── MTARPSession creation ─────────────────────────────────────────────────────


class TestMTARPSessionCreation:
    def test_has_schema_version_1_0(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        assert s.schema_version == "1.0"

    def test_generates_valid_uuid_session_id(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        uuid.UUID(s.session_id)  # raises if invalid

    def test_two_sessions_have_different_ids(self):
        from aider.relay.session import MTARPSession

        s1 = MTARPSession(task_description="test")
        s2 = MTARPSession(task_description="test")
        assert s1.session_id != s2.session_id

    def test_stores_task_description(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="add OAuth login")
        assert s.task_description == "add OAuth login"

    def test_default_handoff_reason_is_exhausted(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        assert s.handoff_reason == "exhausted"

    def test_default_tier_is_agentic_cli(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        assert s.outgoing_tier == "agentic_cli"

    def test_provider_history_empty_by_default(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        assert s.provider_history == []


# ── MTARPSession.to_dict() — MTARP schema shape ───────────────────────────────


class TestMTARPSessionToDict:
    def test_top_level_keys_present(self):
        from aider.relay.session import MTARPSession

        d = MTARPSession(task_description="test").to_dict()
        assert "schema_version" in d
        assert "session_id" in d
        assert "task" in d
        assert "git" in d
        assert "handoff" in d
        assert "provider_history" in d

    def test_task_section_structure(self):
        from aider.relay.session import MTARPSession

        d = MTARPSession(task_description="add OAuth login").to_dict()
        assert d["task"]["description"] == "add OAuth login"
        assert "created_at" in d["task"]

    def test_git_section_structure(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(
            task_description="test", git_head="abc123", git_branch="main", git_diff_since="def456"
        )
        d = s.to_dict()
        assert d["git"]["head"] == "abc123"
        assert d["git"]["branch"] == "main"
        assert d["git"]["diff_since"] == "def456"

    def test_handoff_section_structure(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(
            task_description="test", outgoing_provider="claude-code", handoff_reason="exhausted"
        )
        d = s.to_dict()
        assert d["handoff"]["outgoing_provider"] == "claude-code"
        assert d["handoff"]["reason"] == "exhausted"
        assert d["handoff"]["outgoing_tier"] == "agentic_cli"
        assert "at" in d["handoff"]

    def test_is_json_serializable(self):
        from aider.relay.session import MTARPSession

        d = MTARPSession(task_description="test").to_dict()
        json.dumps(d)  # must not raise


# ── MTARPSession disk I/O ─────────────────────────────────────────────────────


class TestMTARPSessionDiskIO:
    def test_write_creates_file(self, tmp_path):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        path = tmp_path / "session.json"
        s.write(path)
        assert path.exists()

    def test_written_file_is_valid_json(self, tmp_path):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        path = tmp_path / "session.json"
        s.write(path)
        data = json.loads(path.read_text())
        assert data["schema_version"] == "1.0"

    def test_write_creates_parent_directories(self, tmp_path):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        path = tmp_path / "nested" / "dir" / "session.json"
        s.write(path)
        assert path.exists()

    def test_round_trip_preserves_fields(self, tmp_path):
        from aider.relay.session import MTARPSession

        s = MTARPSession(
            task_description="add OAuth login", outgoing_provider="claude-code", git_head="abc123"
        )
        path = tmp_path / "session.json"
        s.write(path)
        loaded = MTARPSession.read(path)
        assert loaded.task_description == "add OAuth login"
        assert loaded.session_id == s.session_id
        assert loaded.outgoing_provider == "claude-code"
        assert loaded.git_head == "abc123"

    def test_round_trip_preserves_provider_history(self, tmp_path):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        s.add_provider_run(
            provider="claude-code",
            tier="agentic_cli",
            session_id="abc123",
            started_at="2026-04-30T00:00:00Z",
            ended_at="2026-04-30T01:00:00Z",
            end_reason="exhausted",
        )
        path = tmp_path / "session.json"
        s.write(path)
        loaded = MTARPSession.read(path)
        assert len(loaded.provider_history) == 1
        assert loaded.provider_history[0]["provider"] == "claude-code"


# ── MTARPSession.add_provider_run() ──────────────────────────────────────────


class TestMTARPSessionProviderHistory:
    def test_add_provider_run_appends_entry(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        s.add_provider_run(
            provider="claude-code",
            tier="agentic_cli",
            session_id="abc",
            started_at="2026-04-30T00:00:00Z",
            ended_at=None,
            end_reason="exhausted",
        )
        assert len(s.provider_history) == 1
        run = s.provider_history[0]
        assert run["provider"] == "claude-code"
        assert run["tier"] == "agentic_cli"
        assert run["session_id"] == "abc"
        assert run["end_reason"] == "exhausted"

    def test_multiple_runs_accumulate(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        s.add_provider_run(
            provider="claude-code",
            tier="agentic_cli",
            session_id="a",
            started_at="2026-04-30T00:00:00Z",
            ended_at=None,
            end_reason="exhausted",
        )
        s.add_provider_run(
            provider="codex",
            tier="agentic_cli",
            session_id="b",
            started_at="2026-04-30T01:00:00Z",
            ended_at=None,
            end_reason="exhausted",
        )
        assert len(s.provider_history) == 2
        assert s.provider_history[1]["provider"] == "codex"

    def test_provider_history_in_to_dict(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession(task_description="test")
        s.add_provider_run(
            provider="claude-code",
            tier="agentic_cli",
            session_id="abc",
            started_at="2026-04-30T00:00:00Z",
            ended_at=None,
            end_reason="exhausted",
        )
        d = s.to_dict()
        assert len(d["provider_history"]) == 1
        assert d["provider_history"][0]["provider"] == "claude-code"


# ── MTARPSession.create() factory ────────────────────────────────────────────


class TestMTARPSessionFactory:
    def test_create_sets_task_description(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession.create(task="add OAuth login", primary_provider="claude-code")
        assert s.task_description == "add OAuth login"

    def test_create_sets_outgoing_provider(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession.create(task="test", primary_provider="claude-code")
        assert s.outgoing_provider == "claude-code"

    def test_create_sets_task_created_at(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession.create(task="test", primary_provider="claude-code")
        assert s.task_created_at  # non-empty ISO timestamp

    def test_create_captures_git_state_or_falls_back(self):
        from aider.relay.session import MTARPSession

        s = MTARPSession.create(task="test", primary_provider="claude-code")
        # git_diff_since should be a SHA or empty string — never None, never an error
        assert isinstance(s.git_diff_since, str)
        assert s.git_diff_since is not None

    def test_create_graceful_when_git_not_available(self):
        from aider.relay.session import MTARPSession

        with patch("subprocess.check_output", side_effect=OSError("git not found")):
            s = MTARPSession.create(task="test", primary_provider="claude-code")
        assert s.task_description == "test"
        assert s.git_head == ""
        assert s.git_branch == ""


# ── relay() writes session.json on exhaustion ─────────────────────────────────


class TestRelayWritesSession:
    """Integration tests: relay() must write session.json when a provider exhausts."""

    def _run_relay(self, primary_turns, fallback_turns, tmp_path, sim_exhaust_after=0):
        from scripts.relay_loop import relay

        primary = MockProvider(primary_turns, session_id="primary-session")
        fallback = MockProvider(fallback_turns, session_id="fallback-session")

        with patch("scripts.relay_loop.make_provider") as mock_make:
            mock_make.side_effect = lambda name: primary if name == "claude" else fallback
            with patch("builtins.input", side_effect=EOFError()):
                asyncio.run(
                    relay(
                        "test task",
                        "claude",
                        "codex",
                        sim_exhaust_after=sim_exhaust_after,
                        session_dir=str(tmp_path),
                    )
                )
        return primary, fallback

    def test_session_json_written_on_real_exhaustion(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        assert (tmp_path / "session.json").exists()

    def test_session_json_written_on_sim_exhaustion(self, tmp_path):
        self._run_relay([success_turn()], [success_turn()], tmp_path, sim_exhaust_after=1)
        assert (tmp_path / "session.json").exists()

    def test_session_json_not_written_when_no_exhaustion(self, tmp_path):
        # Single successful turn, no exhaustion → no session.json written
        self._run_relay([success_turn()], [], tmp_path)
        assert not (tmp_path / "session.json").exists()

    def test_session_json_task_description(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        data = json.loads((tmp_path / "session.json").read_text())
        assert data["task"]["description"] == "test task"

    def test_session_json_outgoing_provider_is_exhausted_one(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        data = json.loads((tmp_path / "session.json").read_text())
        assert data["handoff"]["outgoing_provider"] == "claude"

    def test_session_json_handoff_reason_is_exhausted(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        data = json.loads((tmp_path / "session.json").read_text())
        assert data["handoff"]["reason"] == "exhausted"

    def test_session_json_is_valid_mtarp_schema(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        data = json.loads((tmp_path / "session.json").read_text())
        assert data["schema_version"] == "1.0"
        assert "session_id" in data
        assert "task" in data
        assert "git" in data
        assert "handoff" in data
        assert "provider_history" in data

    def test_session_json_provider_history_records_exhausted_provider(self, tmp_path):
        self._run_relay([exhausted_turn()], [success_turn()], tmp_path)
        data = json.loads((tmp_path / "session.json").read_text())
        history = data["provider_history"]
        assert len(history) >= 1
        assert history[0]["provider"] == "claude"
        assert history[0]["end_reason"] == "exhausted"


# ── handoff prompt includes session reference ─────────────────────────────────


class TestHandoffPromptWithSession:
    def test_handoff_prompt_references_session_file(self, tmp_path):
        """When session_dir is provided, handoff prompt should mention the session file."""
        from scripts.relay_loop import relay

        primary = MockProvider([exhausted_turn()], session_id="p-session")

        received_prompts = []

        async def capture_and_run():
            with patch("scripts.relay_loop.make_provider") as mock_make:

                def make(name):
                    if name == "claude":
                        return primary

                    # Wrap fallback to capture prompt
                    class CapturingProvider(MockProvider):
                        async def run_turn(self, prompt):
                            received_prompts.append(prompt)
                            async for e in super().run_turn(prompt):
                                yield e

                    return CapturingProvider([success_turn()])

                mock_make.side_effect = make
                with patch("builtins.input", side_effect=EOFError()):
                    await relay(
                        "test task",
                        "claude",
                        "codex",
                        session_dir=str(tmp_path),
                    )

        asyncio.run(capture_and_run())
        assert received_prompts, "fallback provider was never called"
        handoff_text = received_prompts[0]
        assert "session.json" in handoff_text or "aider-relay" in handoff_text
