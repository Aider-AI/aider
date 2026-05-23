"""
Copied and adapted from ~/.hermes/hermes-agent/tests/acp/test_server.py
Copyright (c) 2025 Nous Research (MIT License)

Changes made:
- Adapted code to `AiderACPAgent` and `aider.acp_adapter`.
- Replaced `agent_factory` with `coder_factory`.
- Removed `TestAuthenticate` since Aider doesn't implement internal authentication providers.
- Adapted `TestPrompt` from `run_conversation` assertions to drive `coder.run` triggers.
- Removed Hermse-specific Slash commands tests.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

import acp
from acp.schema import (
    AgentCapabilities,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    ResumeSessionResponse,
    SessionInfo,
    TextContentBlock,
)
from aider.acp_adapter.server import AiderACPAgent
from aider.acp_adapter.session import SessionManager

from aider import __version__ as AIDER_VERSION


@pytest.fixture()
def mock_manager():
    """SessionManager with a mock coder factory."""
    # Adapted: agent_factory -> coder_factory
    return SessionManager(coder_factory=lambda: MagicMock(name="MockCoder"))


@pytest.fixture()
def agent(mock_manager):
    """AiderACPAgent backed by a mock session manager."""
    return AiderACPAgent(session_manager=mock_manager)


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_returns_correct_protocol_version(self, agent):
        resp = await agent.initialize(protocol_version=1)
        assert isinstance(resp, InitializeResponse)
        assert resp.protocol_version == acp.PROTOCOL_VERSION

    @pytest.mark.asyncio
    async def test_initialize_returns_agent_info(self, agent):
        resp = await agent.initialize(protocol_version=1)
        assert resp.agent_info is not None
        assert isinstance(resp.agent_info, Implementation)
        assert resp.agent_info.name == "aider-acp"
        assert resp.agent_info.version == AIDER_VERSION

    @pytest.mark.asyncio
    async def test_initialize_returns_capabilities(self, agent):
        resp = await agent.initialize(protocol_version=1)
        caps = resp.agent_capabilities
        assert isinstance(caps, AgentCapabilities)
        assert caps.session_capabilities is not None
        assert caps.session_capabilities.fork is not None
        assert caps.session_capabilities.list is not None


# ---------------------------------------------------------------------------
# new_session / cancel / load / resume
# ---------------------------------------------------------------------------


class TestSessionOps:
    @pytest.mark.asyncio
    async def test_new_session_creates_session(self, agent):
        resp = await agent.new_session(cwd="/home/user/project")
        assert isinstance(resp, NewSessionResponse)
        assert resp.session_id
        state = agent.session_manager.get_session(resp.session_id)
        assert state is not None
        assert state.cwd == "/home/user/project"

    @pytest.mark.asyncio
    async def test_cancel_sets_event(self, agent):
        resp = await agent.new_session(cwd=".")
        state = agent.session_manager.get_session(resp.session_id)
        assert not state.cancel_event.is_set()
        await agent.cancel(session_id=resp.session_id)
        assert state.cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_session_is_noop(self, agent):
        # Should not raise
        await agent.cancel(session_id="does-not-exist")

    @pytest.mark.asyncio
    async def test_load_session_returns_response(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        load_resp = await agent.load_session(cwd="/tmp", session_id=resp.session_id)
        assert isinstance(load_resp, LoadSessionResponse)

    @pytest.mark.asyncio
    async def test_load_session_not_found_returns_none(self, agent):
        resp = await agent.load_session(cwd="/tmp", session_id="bogus")
        assert resp is None

    @pytest.mark.asyncio
    async def test_resume_session_returns_response(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        resume_resp = await agent.resume_session(cwd="/tmp", session_id=resp.session_id)
        assert isinstance(resume_resp, ResumeSessionResponse)

    @pytest.mark.asyncio
    async def test_resume_session_creates_new_if_missing(self, agent):
        resume_resp = await agent.resume_session(cwd="/tmp", session_id="nonexistent")
        assert isinstance(resume_resp, ResumeSessionResponse)


# ---------------------------------------------------------------------------
# list / fork
# ---------------------------------------------------------------------------


class TestListAndFork:
    @pytest.mark.asyncio
    async def test_list_sessions(self, agent):
        await agent.new_session(cwd="/a")
        await agent.new_session(cwd="/b")
        resp = await agent.list_sessions()
        assert isinstance(resp, ListSessionsResponse)
        assert len(resp.sessions) == 2

    @pytest.mark.asyncio
    async def test_fork_session(self, agent):
        new_resp = await agent.new_session(cwd="/original")
        fork_resp = await agent.fork_session(cwd="/forked", session_id=new_resp.session_id)
        assert fork_resp.session_id
        assert fork_resp.session_id != new_resp.session_id


# ---------------------------------------------------------------------------
# prompt
# ---------------------------------------------------------------------------


class TestPrompt:
    @pytest.mark.asyncio
    async def test_prompt_returns_refusal_for_unknown_session(self, agent):
        prompt = [TextContentBlock(type="text", text="hello")]
        resp = await agent.prompt(prompt=prompt, session_id="nonexistent")
        assert isinstance(resp, PromptResponse)
        assert resp.stop_reason == "refusal"

    @pytest.mark.asyncio
    async def test_prompt_returns_end_turn_for_empty_message(self, agent):
        new_resp = await agent.new_session(cwd=".")
        prompt = [TextContentBlock(type="text", text="   ")]
        resp = await agent.prompt(prompt=prompt, session_id=new_resp.session_id)
        assert resp.stop_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_prompt_runs_coder(self, agent):
        """The prompt method should call coder.run with extracted message."""
        new_resp = await agent.new_session(cwd=".")
        state = agent.session_manager.get_session(new_resp.session_id)

        # Mock the coder.run
        from unittest.mock import MagicMock
        state.coder.run = MagicMock()
        state.coder.io = MagicMock()
        state.coder.io.encoding = "utf-8"  # Prevent open() failures

        # Set up a mock connection
        mock_conn = MagicMock(spec=acp.Client)
        agent._conn = mock_conn

        prompt = [TextContentBlock(type="text", text="hello Aider")]
        # Patch the loop.run_in_executor to hit synchronously
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock()
            
            # Since run_in_executor is mocked and won't actually call _run_coder,
            # we will just verify the prompt call routes correctly by extracting and validating triggers.
            await agent.prompt(prompt=prompt, session_id=new_resp.session_id)
            
            # Get the func called in run_in_executor
            call_args = mock_loop.return_value.run_in_executor.call_args
            assert call_args is not None
            # Extract the actual runnable func
            runner = call_args[0][1]
            
            # Trigger it manually to test coder.run()
            runner()
            state.coder.run.assert_called_once_with(with_message="hello Aider")

    @pytest.mark.asyncio
    async def test_prompt_cancelled_returns_cancelled_stop_reason(self, agent):
        """If cancel is called during prompt, stop_reason should be 'cancelled'."""
        new_resp = await agent.new_session(cwd=".")
        state = agent.session_manager.get_session(new_resp.session_id)

        # Mock coder.run that simulates a cancellation trigger
        def mock_run(*args, **kwargs):
            state.cancel_event.set()

        state.coder.run = mock_run
        state.coder.io = MagicMock()
        state.coder.io.encoding = "utf-8"  # Prevent open() failures

        mock_conn = MagicMock(spec=acp.Client)
        agent._conn = mock_conn

        prompt = [TextContentBlock(type="text", text="do something")]
        with patch("asyncio.get_running_loop") as mock_loop:
            # Bypass executor threading directly
            async def run_sync_mock(executor, func, *args):
                func()
            mock_loop.return_value.run_in_executor = run_sync_mock
            
            resp = await agent.prompt(prompt=prompt, session_id=new_resp.session_id)
            assert resp.stop_reason == "cancelled"
