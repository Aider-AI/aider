"""
Copied and adapted from ~/.hermes/hermes-agent/acp_adapter/server.py
Copyright (c) 2025 Nous Research (MIT License)

Changes made:
- Adapted HermesACPAgent to AiderACPAgent.
- Handles `prompt` by swapping `coder.io` to incremental `ACPInputOutput` and calling `coder.run(with_message)`.
- Reused initialize/authenticate and session lifecycle methods.

Merge Note: If updating from Hermes, preserve session setup and cancellation hooks.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import acp
from acp.schema import (
    AgentCapabilities,
    AuthenticateResponse,
    ClientCapabilities,
    EmbeddedResourceContentBlock,
    ForkSessionResponse,
    ImageContentBlock,
    AudioContentBlock,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    ResumeSessionResponse,
    ResourceContentBlock,
    SessionCapabilities,
    SessionForkCapabilities,
    SessionListCapabilities,
    SessionInfo,
    TextContentBlock,
    Usage,
)

from .session import SessionManager, SessionState
from .io import ACPInputOutput

logger = logging.getLogger(__name__)

from aider import __version__ as AIDER_VERSION

# Thread pool for running Coder.run() in parallel
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="acp-aider")


def _extract_text(
    prompt: list[
        TextContentBlock
        | ImageContentBlock
        | AudioContentBlock
        | ResourceContentBlock
        | EmbeddedResourceContentBlock
    ],
) -> str:
    """Extract plain text from ACP content blocks."""
    parts: list[str] = []
    for block in prompt:
        if isinstance(block, TextContentBlock):
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(str(block.text))
    return "\n".join(parts)


class AiderACPAgent(acp.Agent):
    """ACP Agent implementation wrapping Aider Coder conversation runner."""

    def __init__(self, session_manager: SessionManager | None = None):
        super().__init__()
        self.session_manager = session_manager or SessionManager()
        self._conn: Optional[acp.Client] = None

    # ---- Connection lifecycle -----------------------------------------------

    def on_connect(self, conn: acp.Client) -> None:
        """Store the client connection for sending session updates."""
        self._conn = conn
        logger.info("ACP client connected for Aider")

    # ---- ACP lifecycle ------------------------------------------------------

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: ClientCapabilities | None = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        client_name = client_info.name if client_info else "unknown"
        logger.info("Initialize from %s (protocol v%s)", client_name, protocol_version)

        return InitializeResponse(
            protocol_version=acp.PROTOCOL_VERSION,
            agent_info=Implementation(name="aider-acp", version=AIDER_VERSION),
            agent_capabilities=AgentCapabilities(
                session_capabilities=SessionCapabilities(
                    fork=SessionForkCapabilities(),
                    list=SessionListCapabilities(),
                ),
            ),
            auth_methods=None,  # standard auth for now
        )

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse | None:
        return AuthenticateResponse()

    # ---- Session management -------------------------------------------------

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        state = self.session_manager.create_session(cwd=cwd)
        logger.info("New session %s (cwd=%s)", state.session_id, cwd)
        return NewSessionResponse(session_id=state.session_id)

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ) -> LoadSessionResponse | None:
        state = self.session_manager.update_cwd(session_id, cwd)
        if state is None:
            logger.warning("load_session: session %s not found", session_id)
            return None
        logger.info("Loaded session %s", session_id)
        return LoadSessionResponse()

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        state = self.session_manager.update_cwd(session_id, cwd)
        if state is None:
            logger.warning("resume_session: session %s not found, creating new", session_id)
            state = self.session_manager.create_session(cwd=cwd)
        logger.info("Resumed session %s", state.session_id)
        return ResumeSessionResponse()

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        state = self.session_manager.get_session(session_id)
        if state and state.cancel_event:
            state.cancel_event.set()
            # Aider's Coder doesn't have an interrupt method easily callable from thread,
            # but setting and reading from cancel_event inside IO works.
            logger.info("Cancelled session %s", session_id)

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        state = self.session_manager.fork_session(session_id, cwd=cwd)
        new_id = state.session_id if state else ""
        logger.info("Forked session %s -> %s", session_id, new_id)
        return ForkSessionResponse(session_id=new_id)

    async def list_sessions(
        self,
        cursor: str | None = None,
        cwd: str | None = None,
        **kwargs: Any,
    ) -> ListSessionsResponse:
        infos = self.session_manager.list_sessions()
        sessions = [
            SessionInfo(session_id=s["session_id"], cwd=s["cwd"])
            for s in infos
        ]
        return ListSessionsResponse(sessions=sessions)

    # ---- Prompt (core) ------------------------------------------------------

    async def prompt(
        self,
        prompt: list[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """Run Aider on the user's prompt and stream responses to the client."""
        state = self.session_manager.get_session(session_id)
        if state is None:
            logger.error("prompt: session %s not found", session_id)
            return PromptResponse(stop_reason="refusal")

        user_text = _extract_text(prompt).strip()
        if not user_text:
            return PromptResponse(stop_reason="end_turn")

        logger.info("Prompt on session %s: %s", session_id, user_text[:100])

        conn = self._conn
        loop = asyncio.get_running_loop()

        if state.cancel_event:
            state.cancel_event.clear()

        coder = state.coder
        original_io = coder.io

        # Swap to ACP InputOutput
        coder.io = ACPInputOutput.from_existing(
            existing_io=original_io,
            conn=conn,
            session_id=session_id,
            loop=loop,
        )

        def _run_coder() -> None:
            try:
                # Drive aider with the user message
                # aider automatically appends response stream to io
                coder.run(with_message=user_text)
            except Exception:
                logger.exception("Coder Error in session %s", session_id)

        try:
            await loop.run_in_executor(_executor, _run_coder)
        except Exception:
            logger.exception("Executor error for session %s", session_id)
        finally:
            # Restore state or InputOutput
            coder.io = original_io

        stop_reason = "cancelled" if state.cancel_event and state.cancel_event.is_set() else "end_turn"
        return PromptResponse(stop_reason=stop_reason)
