"""
Copied and adapted from ~/.hermes/hermes-agent/acp_adapter/session.py
Copyright (c) 2025 Nous Research (MIT License)

Changes made:
- Renamed _make_agent to _make_coder.
- Used aider.main(return_coder=True) for instantiating the Coder correctly with all args load logic.
- SessionState now holds `coder` instead of `agent`.

Merge Note: If updating from Hermes, preserve SessionManager Lock handling and fork deepcopy strategy.
"""

from __future__ import annotations

import copy
import logging
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Tracks per-session state for an ACP-managed Aider coder."""

    session_id: str
    coder: Any  # Aider Coder instance
    cwd: str = "."
    model: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    cancel_event: Any = None  # threading.Event


class SessionManager:
    """Thread-safe manager for ACP sessions backed by Aider Coder instances."""

    def __init__(self, coder_factory=None):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()
        self._coder_factory = coder_factory

    # ---- public API ---------------------------------------------------------

    def create_session(self, cwd: str = ".") -> SessionState:
        """Create a new session with a unique ID and a fresh Coder."""
        import threading

        session_id = str(uuid.uuid4())
        coder = self._make_coder(session_id=session_id, cwd=cwd)
        state = SessionState(
            session_id=session_id,
            coder=coder,
            cwd=cwd,
            model=getattr(coder, "main_model", {}).get("name", "") if hasattr(coder, "main_model") else "",
            cancel_event=threading.Event(),
        )
        with self._lock:
            self._sessions[session_id] = state
        logger.info("Created ACP session %s (cwd=%s)", session_id, cwd)
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Return the session for *session_id*, or ``None``."""
        with self._lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed."""
        with self._lock:
            existed = self._sessions.pop(session_id, None) is not None
        return existed

    def fork_session(self, session_id: str, cwd: str = ".") -> Optional[SessionState]:
        """Deep-copy a session's history into a new session."""
        import threading

        with self._lock:
            original = self._sessions.get(session_id)
            if original is None:
                return None

            new_id = str(uuid.uuid4())
            coder = self._make_coder(
                session_id=new_id,
                cwd=cwd,
                model=original.model or None,
            )
            state = SessionState(
                session_id=new_id,
                coder=coder,
                cwd=cwd,
                model=getattr(coder, "main_model", {}).get("name", original.model) if hasattr(coder, "main_model") else original.model,
                history=copy.deepcopy(original.history),
                cancel_event=threading.Event(),
            )
            self._sessions[new_id] = state
        logger.info("Forked ACP session %s -> %s", session_id, new_id)
        return state

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return lightweight info dicts for all sessions."""
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "cwd": s.cwd,
                    "model": s.model,
                    "history_len": len(s.history),
                }
                for s in self._sessions.values()
            ]

    def update_cwd(self, session_id: str, cwd: str) -> Optional[SessionState]:
        """Update the working directory for a session."""
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return None
            state.cwd = cwd
        return state

    def cleanup(self) -> None:
        """Remove all sessions."""
        with self._lock:
            self._sessions.clear()

    # ---- internal -----------------------------------------------------------

    def _make_coder(
        self,
        *,
        session_id: str,
        cwd: str,
        model: str | None = None,
    ):
        if self._coder_factory is not None:
            return self._coder_factory()

        # Call Aider's main to build a Coder correctly with standard flags
        from aider.main import main
        import os
        import sys

        old_cwd = os.getcwd()
        try:
            if cwd and cwd != ".":
                try:
                    os.chdir(cwd)
                except OSError:
                    logger.warning("Failed to chdir to %s for session creation", cwd)

            argv = ["--no-pretty", "--no-analytics"]
            if model:
                argv += ["--model", model]
            
            # Run main with return_coder=True
            coder = main(argv=argv, return_coder=True)
            return coder

        finally:
            if os.getcwd() != old_cwd:
                try:
                    os.chdir(old_cwd)
                except OSError:
                    pass
