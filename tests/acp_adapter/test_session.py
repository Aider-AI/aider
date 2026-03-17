"""
Copied and adapted from ~/.hermes/hermes-agent/tests/acp/test_session.py
Copyright (c) 2025 Nous Research (MIT License)

Changes made:
- Adapted imports to `aider.acp_adapter.session`.
- Replaced `agent_factory` with `coder_factory`.
- Replaced check on `.agent` with `.coder`.
- Removed `_register_task_cwd` monkeypatch test as it is specific to Hermes.
"""

import pytest
from unittest.mock import MagicMock

from aider.acp_adapter.session import SessionManager, SessionState


@pytest.fixture()
def manager():
    """SessionManager with a mock coder factory."""
    # Adapted: agent_factory -> coder_factory
    return SessionManager(coder_factory=lambda: MagicMock(name="MockCoder"))


# ---------------------------------------------------------------------------
# create / get
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_create_session_returns_state(self, manager):
        state = manager.create_session(cwd="/tmp/work")
        assert isinstance(state, SessionState)
        assert state.cwd == "/tmp/work"
        assert state.session_id
        assert state.history == []
        # Adapted: .agent -> .coder
        assert state.coder is not None

    def test_session_ids_are_unique(self, manager):
        s1 = manager.create_session()
        s2 = manager.create_session()
        assert s1.session_id != s2.session_id

    def test_get_session(self, manager):
        state = manager.create_session()
        fetched = manager.get_session(state.session_id)
        assert fetched is state

    def test_get_nonexistent_session_returns_none(self, manager):
        assert manager.get_session("does-not-exist") is None


# ---------------------------------------------------------------------------
# fork
# ---------------------------------------------------------------------------


class TestForkSession:
    def test_fork_session_deep_copies_history(self, manager):
        # Adapted for basic history list appending
        original = manager.create_session()
        original.history.append({"role": "user", "content": "hello"})
        original.history.append({"role": "assistant", "content": "hi"})

        forked = manager.fork_session(original.session_id, cwd="/new")
        assert forked is not None

        # History should be equal in content
        assert len(forked.history) == 2
        assert forked.history[0]["content"] == "hello"

        # But a deep copy — mutating one doesn't affect the other
        forked.history.append({"role": "user", "content": "extra"})
        assert len(original.history) == 2
        assert len(forked.history) == 3

    def test_fork_session_has_new_id(self, manager):
        original = manager.create_session()
        forked = manager.fork_session(original.session_id)
        assert forked is not None
        assert forked.session_id != original.session_id

    def test_fork_nonexistent_returns_none(self, manager):
        assert manager.fork_session("bogus-id") is None


# ---------------------------------------------------------------------------
# list / cleanup / remove
# ---------------------------------------------------------------------------


class TestListAndCleanup:
    def test_list_sessions_empty(self, manager):
        assert manager.list_sessions() == []

    def test_list_sessions_returns_created(self, manager):
        s1 = manager.create_session(cwd="/a")
        s2 = manager.create_session(cwd="/b")
        listing = manager.list_sessions()
        ids = {s["session_id"] for s in listing}
        assert s1.session_id in ids
        assert s2.session_id in ids
        assert len(listing) == 2

    def test_cleanup_clears_all(self, manager):
        manager.create_session()
        manager.create_session()
        assert len(manager.list_sessions()) == 2
        manager.cleanup()
        assert manager.list_sessions() == []

    def test_remove_session(self, manager):
        state = manager.create_session()
        assert manager.remove_session(state.session_id) is True
        assert manager.get_session(state.session_id) is None
        # Removing again returns False
        assert manager.remove_session(state.session_id) is False
