"""Session management utilities for Aider."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from aider import models


class SessionManager:
    """Manages chat session saving, listing, and loading."""

    def __init__(self, coder, io):
        self.coder = coder
        self.io = io

    def _get_session_directory(self) -> Path:
        """Get the session directory, creating it if necessary."""
        session_dir = Path(self.coder.abs_root_path(".aider/sessions"))
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def save_session(self, session_name: str, output=True) -> bool:
        """Save the current chat session to a named file."""
        if not session_name:
            if output:
                self.io.tool_error("Please provide a session name.")
            return False

        session_name = session_name.replace(".json", "")
        session_dir = self._get_session_directory()
        session_file = session_dir / f"{session_name}.json"

        if session_file.exists():
            if output:
                self.io.tool_warning(f"Session '{session_name}' already exists. Overwriting.")

        try:
            session_data = self._build_session_data(session_name)
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)

            if output:
                self.io.tool_output(f"Session saved: {session_file}")

            return True

        except Exception as e:
            self.io.tool_error(f"Error saving session: {e}")
            return False

    def list_sessions(self) -> List[Dict]:
        """List all saved sessions with metadata."""
        session_dir = self._get_session_directory()
        session_files = list(session_dir.glob("*.json"))

        if not session_files:
            self.io.tool_output("No saved sessions found.")
            return []

        sessions = []
        for session_file in sorted(session_files, key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_data = json.load(f)

                session_info = {
                    "name": session_file.stem,
                    "file": session_file,
                    "model": session_data.get("model", "unknown"),
                    "edit_format": session_data.get("edit_format", "unknown"),
                    "num_messages": len(
                        session_data.get("chat_history", {}).get("done_messages", [])
                    ) + len(session_data.get("chat_history", {}).get("cur_messages", [])),
                    "num_files": (
                        len(session_data.get("files", {}).get("editable", []))
                        + len(session_data.get("files", {}).get("read_only", []))
                        + len(session_data.get("files", {}).get("read_only_stubs", []))
                    ),
                }
                sessions.append(session_info)

            except Exception as e:
                self.io.tool_output(f"  {session_file.stem} [error reading: {e}]")

        return sessions

    def load_session(self, session_identifier: str) -> bool:
        """Load a saved session by name or file path."""
        if not session_identifier:
            self.io.tool_error("Please provide a session name or file path.")
            return False

        # Try to find the session file
        session_file = self._find_session_file(session_identifier)
        if not session_file:
            return False

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except Exception as e:
            self.io.tool_error(f"Error loading session: {e}")
            return False

        # Verify session format
        if not isinstance(session_data, dict) or "version" not in session_data:
            self.io.tool_error("Invalid session format.")
            return False

        # Apply session data
        return self._apply_session_data(session_data, session_file)

    def _build_session_data(self, session_name) -> Dict:
        """Build session data dictionary from current coder state."""
        # Get relative paths for all files
        editable_files = [
            self.coder.get_rel_fname(abs_fname) for abs_fname in self.coder.abs_fnames
        ]
        read_only_files = [
            self.coder.get_rel_fname(abs_fname) for abs_fname in self.coder.abs_read_only_fnames
        ]
        read_only_stubs_files = [
            self.coder.get_rel_fname(abs_fname)
            for abs_fname in self.coder.abs_read_only_stubs_fnames
        ]

        return {
            "version": 1,
            "session_name": session_name,
            "model": self.coder.main_model.name,
            "weak_model": self.coder.main_model.weak_model.name,
            "editor_model": self.coder.main_model.editor_model.name,
            "editor_edit_format": self.coder.main_model.editor_edit_format,
            "edit_format": self.coder.edit_format,
            "chat_history": {
                "done_messages": self.coder.done_messages,
                "cur_messages": self.coder.cur_messages,
            },
            "files": {
                "editable": editable_files,
                "read_only": read_only_files,
                "read_only_stubs": read_only_stubs_files,
            },
            "settings": {
                "auto_commits": self.coder.auto_commits,
                "auto_lint": self.coder.auto_lint,
                "auto_test": self.coder.auto_test,
            },
        }

    def _find_session_file(self, session_identifier: str) -> Optional[Path]:
        """Find session file by name or path."""
        # Check if it's a direct file path
        session_file = Path(session_identifier)
        if session_file.exists():
            return session_file

        # Check if it's a session name in the sessions directory
        session_dir = self._get_session_directory()

        # Try with .json extension
        if not session_identifier.endswith(".json"):
            session_file = session_dir / f"{session_identifier}.json"
            if session_file.exists():
                return session_file

        session_file = session_dir / f"{session_identifier}"
        if session_file.exists():
            return session_file

        self.io.tool_error(f"Session not found: {session_identifier}")
        self.io.tool_output("Use /list-sessions to see available sessions.")
        return None

    def _apply_session_data(self, session_data: Dict, session_file: Path) -> bool:
        """Apply session data to current coder state."""
        try:
            # Clear current state
            self.coder.abs_fnames = set()
            self.coder.abs_read_only_fnames = set()
            self.coder.abs_read_only_stubs_fnames = set()
            self.coder.done_messages = []
            self.coder.cur_messages = []

            # Load chat history
            chat_history = session_data.get("chat_history", {})
            self.coder.done_messages = chat_history.get("done_messages", [])
            self.coder.cur_messages = chat_history.get("cur_messages", [])

            # Load files
            files = session_data.get("files", {})
            for rel_fname in files.get("editable", []):
                abs_fname = self.coder.abs_root_path(rel_fname)
                if os.path.exists(abs_fname):
                    self.coder.abs_fnames.add(abs_fname)
                else:
                    self.io.tool_warning(f"File not found, skipping: {rel_fname}")

            for rel_fname in files.get("read_only", []):
                abs_fname = self.coder.abs_root_path(rel_fname)
                if os.path.exists(abs_fname):
                    self.coder.abs_read_only_fnames.add(abs_fname)
                else:
                    self.io.tool_warning(f"File not found, skipping: {rel_fname}")

            for rel_fname in files.get("read_only_stubs", []):
                abs_fname = self.coder.abs_root_path(rel_fname)
                if os.path.exists(abs_fname):
                    self.coder.abs_read_only_stubs_fnames.add(abs_fname)
                else:
                    self.io.tool_warning(f"File not found, skipping: {rel_fname}")

            if session_data.get("model"):
                self.coder.main_model = models.Model(
                    session_data.get("model", self.coder.args.model),
                    weak_model=session_data.get("weak_model", self.coder.args.weak_model),
                    editor_model=session_data.get("editor_model", self.coder.args.editor_model),
                    editor_edit_format=session_data.get(
                        "editor_edit_format", self.coder.args.editor_edit_format
                    ),
                    verbose=self.coder.args.verbose,
                )

            # Load settings
            settings = session_data.get("settings", {})
            if "auto_commits" in settings:
                self.coder.auto_commits = settings["auto_commits"]
            if "auto_lint" in settings:
                self.coder.auto_lint = settings["auto_lint"]
            if "auto_test" in settings:
                self.coder.auto_test = settings["auto_test"]

            self.io.tool_output(
                f"Session loaded: {session_data.get('session_name', session_file.stem)}"
            )
            self.io.tool_output(
                f"Model: {session_data.get('model', 'unknown')}, Edit format:"
                f" {session_data.get('edit_format', 'unknown')}"
            )

            # Show summary
            num_messages = len(self.coder.done_messages) + len(self.coder.cur_messages)
            num_files = (
                len(self.coder.abs_fnames)
                + len(self.coder.abs_read_only_fnames)
                + len(self.coder.abs_read_only_stubs_fnames)
            )
            self.io.tool_output(f"Loaded {num_messages} messages and {num_files} files")

            return True

        except Exception as e:
            self.io.tool_error(f"Error applying session data: {e}")
            return False
