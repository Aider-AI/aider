"""
MTARP Phase 1 session envelope.

Implements MTARPSession — a record of what was in progress when a provider
was switched due to exhaustion, per KB-2026-021 / KB-2026-022 / KB-2026-026.

MTARP is a domain-specific A2A extension (KB-2026-026). session.json is the
payload schema; to_a2a_artifact() wraps it for A2A transport when needed.
"""
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class MTARPSession:
    schema_version: str = "1.0"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    task_created_at: str = ""
    git_head: str = ""
    git_branch: str = ""
    git_diff_since: str = ""  # git SHA at session START (diff from here shows what was done)
    handoff_reason: str = "exhausted"
    handoff_at: str = ""
    outgoing_provider: str = ""
    outgoing_tier: str = "agentic_cli"
    provider_history: list = field(default_factory=list)
    # Phase 2 fields (KB-2026-030 Step 6)
    files_in_scope: list = field(default_factory=list)  # files changed during session
    session_summary: str = ""  # LLM-generated summary of what was accomplished

    def to_dict(self) -> dict:
        """Serialize to MTARP schema structure (nested, not flat)."""
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "task": {
                "description": self.task_description,
                "created_at": self.task_created_at,
            },
            "git": {
                "head": self.git_head,
                "branch": self.git_branch,
                "diff_since": self.git_diff_since,
            },
            "handoff": {
                "reason": self.handoff_reason,
                "at": self.handoff_at,
                "outgoing_provider": self.outgoing_provider,
                "outgoing_tier": self.outgoing_tier,
            },
            "provider_history": list(self.provider_history),
            "files_in_scope": list(self.files_in_scope),
            "session_summary": self.session_summary,
        }

    def write(self, path: Path) -> None:
        """Write session.json, creating parent directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def read(cls, path: Path) -> "MTARPSession":
        """Read and deserialize session.json."""
        data = json.loads(Path(path).read_text())
        task = data.get("task", {})
        git = data.get("git", {})
        handoff = data.get("handoff", {})
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            session_id=data.get("session_id", str(uuid.uuid4())),
            task_description=task.get("description", ""),
            task_created_at=task.get("created_at", ""),
            git_head=git.get("head", ""),
            git_branch=git.get("branch", ""),
            git_diff_since=git.get("diff_since", ""),
            handoff_reason=handoff.get("reason", "exhausted"),
            handoff_at=handoff.get("at", ""),
            outgoing_provider=handoff.get("outgoing_provider", ""),
            outgoing_tier=handoff.get("outgoing_tier", "agentic_cli"),
            provider_history=data.get("provider_history", []),
            files_in_scope=data.get("files_in_scope", []),
            session_summary=data.get("session_summary", ""),
        )

    @classmethod
    def create(cls, task: str, primary_provider: str) -> "MTARPSession":
        """Factory: create session capturing current git state. Graceful if git unavailable."""

        def _run(cmd):
            try:
                return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
            except (subprocess.CalledProcessError, OSError):
                return ""

        git_head = _run(["git", "rev-parse", "HEAD"])
        git_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        now = datetime.now(tz=timezone.utc).isoformat()

        return cls(
            task_description=task,
            task_created_at=now,
            git_head=git_head,
            git_branch=git_branch,
            git_diff_since=git_head,  # diff from session start shows what was done
            outgoing_provider=primary_provider,
        )

    def add_provider_run(
        self,
        *,
        provider: str,
        tier: str,
        session_id: str,
        started_at: str,
        ended_at: str | None,
        end_reason: str,
    ) -> None:
        """Append a completed provider run to provider_history."""
        self.provider_history.append(
            {
                "provider": provider,
                "tier": tier,
                "session_id": session_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "end_reason": end_reason,
            }
        )

    _EXTENSION_URI = "https://mtarp.dev/ext/coding-session/v1"

    def to_a2a_artifact(self) -> dict:
        """Wrap this session as an A2A Artifact (KB-2026-026).

        When MTARP is used with an A2A transport layer, the session.json payload
        is embedded here rather than written to a sidecar file.
        """
        return {
            "artifactId": f"mtarp-session-{self.session_id}",
            "name": "mtarp-session",
            "mimeType": "application/json",
            "description": "MTARP session envelope for handoff continuation",
            "extensions": [self._EXTENSION_URI],
            "parts": [{"kind": "text", "text": json.dumps(self.to_dict(), indent=2)}],
        }

    def to_a2a_task_metadata(self) -> dict:
        """Return namespaced metadata keys for an A2A Task (KB-2026-026).

        These allow an MTARP-aware orchestrator to inspect handoff signals from
        the Task object without parsing the full artifact.
        """
        ns = self._EXTENSION_URI
        return {
            f"{ns}/handoff_reason": self.handoff_reason,
            f"{ns}/git_diff_since": self.git_diff_since,
            f"{ns}/outgoing_tier": self.outgoing_tier,
        }

    @staticmethod
    def agent_card_extension(tier: str = "agentic_cli", delivery_mode: str = "pull") -> dict:
        """Return the MTARP extension block for inclusion in an A2A AgentCard (KB-2026-026)."""
        return {
            "uri": MTARPSession._EXTENSION_URI,
            "description": "Git-aware session continuation for exhaustion-triggered handoffs",
            "required": False,
            "params": {
                "tier": tier,
                "delivery_mode": delivery_mode,
                "handoff_signals": ["exhausted", "escalate", "deescalate", "user_request", "error"],
            },
        }
