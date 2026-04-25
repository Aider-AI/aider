"""
ACP InputOutput interface for Aider.

Subclasses InputOutput to stream responses to the ACP client instead of standard terminal Console.
Includes a custom MarkdownStream support that push incremental updates over JSON-RPC.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rich.text import Text
from aider.io import InputOutput

import acp

logger = logging.getLogger(__name__)


def _send_update(
    conn: acp.Client,
    session_id: str,
    loop: asyncio.AbstractEventLoop,
    update: Any,
) -> None:
    """Fire-and-forget an ACP session update from a worker thread."""
    if conn is None:
        return
    try:
        future = asyncio.run_coroutine_threadsafe(
            conn.session_update(session_id, update), loop
        )
        # timeout so it does not lock the runner if connection breaks
        future.result(timeout=5)
    except Exception:
        logger.debug("Failed to send ACP update", exc_info=True)


class ACPMarkdownStream:
    """Streams markdown response chunks back to the ACP client."""

    def __init__(self, conn: acp.Client, session_id: str, loop: asyncio.AbstractEventLoop):
        self.conn = conn
        self.session_id = session_id
        self.loop = loop
        self.previous_text = ""

    def update(self, text: str, final: bool = False) -> None:
        """Called with the full accumulated stream text."""
        if not text:
            return
        
        # Incremental addition
        added = text[len(self.previous_text):]
        if added:
            update = acp.update_agent_message_text(added)
            _send_update(self.conn, self.session_id, self.loop, update)
        
        self.previous_text = text


class ACPInputOutput(InputOutput):
    """Subclass of InputOutput mapping console outputs to stream updates."""

    def __init__(
        self,
        conn: acp.Client,
        session_id: str,
        loop: asyncio.AbstractEventLoop,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.conn = conn
        self.session_id = session_id
        self.loop = loop

    @classmethod
    def from_existing(
        cls,
        existing_io: InputOutput,
        conn: acp.Client,
        session_id: str,
        loop: asyncio.AbstractEventLoop,
    ) -> ACPInputOutput:
        """Construct our subclass copying from an original aider InputOutput."""
        # Create instance without calling __init__ to copy dict directly?
        # Safe way: Init with copied values
        inst = cls(
            conn=conn,
            session_id=session_id,
            loop=loop,
            pretty=False,  # important: keep formatting plain so we can stream raw text
            yes=existing_io.yes,
            input_history_file=existing_io.input_history_file,
            chat_history_file=existing_io.chat_history_file,
            encoding=existing_io.encoding,
            dry_run=existing_io.dry_run,
            llm_history_file=existing_io.llm_history_file,
            multiline_mode=existing_io.multiline_mode,
        )
        return inst

    # ---- Custom support creators ---------------------------------------------

    def get_assistant_mdstream(self) -> ACPMarkdownStream:
        """Provide our custom incremental stream generator."""
        return ACPMarkdownStream(self.conn, self.session_id, self.loop)

    # ---- Overriding standard outputs -----------------------------------------

    def assistant_output(self, message: str, pretty: bool | None = None) -> None:
        """Called for the final message if stream is off or completes."""
        if message:
            update = acp.update_agent_message_text(message)
            _send_update(self.conn, self.session_id, self.loop, update)

    def _tool_message(self, message: str = "", strip: bool = True, color: str | None = None) -> None:
        """Route internal status/errors as updates."""
        if message:
            # Send status as thought/status update so it doesn't pollute assistant stream directly
            update = acp.update_agent_thought_text(message.strip())
            _send_update(self.conn, self.session_id, self.loop, update)

    def tool_error(self, message: str = "", strip: bool = True) -> None:
        if message:
            # For client errors, thought is safe to use
            update = acp.update_agent_thought_text(f"Error: {message.strip()}")
            _send_update(self.conn, self.session_id, self.loop, update)

    def tool_output(self, *messages: Any, log_only: bool = False, bold: bool = False) -> None:
        if log_only or not messages:
            return
        combined_text = " ".join(str(m) for m in messages).strip()
        if combined_text:
            update = acp.update_agent_thought_text(combined_text)
            _send_update(self.conn, self.session_id, self.loop, update)

    def print(self, message: str = "") -> None:
        """Aider generic print."""
        # Generic prints route into thought
        if message and message.strip():
            update = acp.update_agent_thought_text(message.strip())
            _send_update(self.conn, self.session_id, self.loop, update)
