from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .aider_cli import run_aider_once
from .config import SLMSettings
from .git_ops import (
    ensure_repo_ready,
    get_commit,
    get_diff_stat,
    git_has_changes,
    reset_hard,
    run_sanity_checks,
    stage_commit_and_push,
)
from .models import PendingItem, PendingResponse, StatusResponse
from .nats_subscriber import NatsLogSubscriber
from .reasoning import ReasoningDecision, ReasoningEngine


State = Literal[
    "queued",
    "running",
    "pending_approval",
    "approved",
    "pushed",
    "denied",
    "error",
    "no_changes",
]


@dataclass
class ChangeRequest:
    id: str
    prompt: str
    source: Literal["manual", "log"]
    files: list[str] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    state: State = "queued"

    # git metadata
    branch: str | None = None
    base_branch: str | None = None
    base_commit: str | None = None
    commit: str | None = None
    diff_stat: str | None = None

    error: str | None = None

    # approval events
    approved: asyncio.Event = field(default_factory=asyncio.Event)
    denied: asyncio.Event = field(default_factory=asyncio.Event)


class SLMService:
    """In-memory orchestrator.

    This service intentionally serializes all actions because it edits a single working tree.
    """

    def __init__(self, settings: SLMSettings):
        self.settings = settings

        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.requests: dict[str, ChangeRequest] = {}
        self.running_id: str | None = None

        self._stop = asyncio.Event()
        self._worker_task: asyncio.Task | None = None
        self._nats: NatsLogSubscriber | None = None

        self._reasoning = ReasoningEngine()

    async def start(self) -> None:
        self._stop.clear()
        self._worker_task = asyncio.create_task(self._worker_loop())

        # Start log subscriber (best-effort). Missing env vars shouldn't prevent boot.
        if self.settings.nats_subject and self.settings.fly_org and self.settings.fly_api_token:
            self._nats = NatsLogSubscriber(
                nats_url=self.settings.nats_url,
                subject=self.settings.nats_subject,
                queue=self.settings.nats_queue,
                user=self.settings.fly_org,
                password=self.settings.fly_api_token,
                on_log_line=self._handle_log_line,
            )
            await self._nats.start()

    async def stop(self) -> None:
        self._stop.set()
        if self._nats:
            await self._nats.stop()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    def get_status(self) -> StatusResponse:
        queued = self.queue.qsize()
        pending = len([r for r in self.requests.values() if r.state == "pending_approval"])
        return StatusResponse(
            running_id=self.running_id,
            queued=queued,
            pending=pending,
            total=len(self.requests),
        )

    def get_pending(self) -> PendingResponse:
        items: list[PendingItem] = []
        for req in self.requests.values():
            if req.state not in (
                "pending_approval",
                "pushed",
                "approved",
                "denied",
                "error",
                "no_changes",
                "queued",
                "running",
            ):
                continue
            items.append(
                PendingItem(
                    id=req.id,
                    prompt=req.prompt,
                    state=req.state,
                    branch=req.branch,
                    base_branch=req.base_branch,
                    base_commit=req.base_commit,
                    commit=req.commit,
                    diff_stat=req.diff_stat,
                    error=req.error,
                )
            )
        items.sort(key=lambda i: i.id)
        return PendingResponse(items=items)

    async def enqueue_prompt(self, prompt: str, source: Literal["manual", "log"] = "manual") -> str:
        req_id = uuid.uuid4().hex
        self.requests[req_id] = ChangeRequest(id=req_id, prompt=prompt, source=source)
        await self.queue.put(req_id)
        return req_id

    async def approve(self, req_id: str) -> bool:
        req = self.requests.get(req_id)
        if not req or req.state != "pending_approval":
            return False
        req.state = "approved"
        req.approved.set()
        return True

    async def deny(self, req_id: str) -> bool:
        req = self.requests.get(req_id)
        if not req or req.state != "pending_approval":
            return False
        req.state = "denied"
        req.denied.set()
        return True

    async def _handle_log_line(self, log_line: str) -> None:
        decision: ReasoningDecision | None = self._reasoning.decision_from_log(log_line)
        if not decision:
            return

        # Avoid spamming: collapse identical prompts if they are already queued/pending.
        for existing in self.requests.values():
            if (
                existing.prompt == decision.prompt
                and existing.state in ("queued", "running", "pending_approval")
            ):
                return

        req_id = uuid.uuid4().hex
        self.requests[req_id] = ChangeRequest(
            id=req_id, prompt=decision.prompt, files=decision.files, source="log"
        )
        await self.queue.put(req_id)

    async def _worker_loop(self) -> None:
        while not self._stop.is_set():
            req_id = await self.queue.get()
            self.running_id = req_id
            try:
                await self._process(req_id)
            finally:
                self.running_id = None

    async def _process(self, req_id: str) -> None:
        req = self.requests[req_id]
        req.state = "running"

        repo_path = self.settings.repo_path

        try:
            ensure_repo_ready(repo_path, self.settings.repo_git_url, self.settings.push_remote)
        except Exception as e:
            req.state = "error"
            req.error = f"repo not ready: {e}"
            return

        # Work on a dedicated branch.
        branch = f"slm-patch-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{req_id[:8]}"
        req.branch = branch

        try:
            base_branch = self.settings.push_branch
            req.base_branch = base_branch
            base_commit = get_commit(repo_path)
            req.base_commit = base_commit

            # Create/reset branch from origin/base_branch.
            reset_hard(repo_path, f"{self.settings.push_remote}/{base_branch}")
            run_cmd = [
                "git",
                "-C",
                repo_path,
                "checkout",
                "-B",
                branch,
                f"{self.settings.push_remote}/{base_branch}",
            ]
            _run_subprocess(run_cmd)

            # Run aider with our instruction.
            await asyncio.to_thread(
                run_aider_once,
                repo_path=repo_path,
                prompt=req.prompt,
                rules_path=self.settings.rules_path,
                model=self.settings.aider_model,
                editor_model=self.settings.aider_editor_model,
                weak_model=self.settings.aider_weak_model,
                architect=self.settings.aider_architect,
                files=req.files,
            )

            if not git_has_changes(repo_path):
                req.state = "no_changes"
                return

            # Pre-commit sanity check. If these fail, revert changes.
            ok, err = await asyncio.to_thread(
                run_sanity_checks,
                repo_path,
                cargo_cmd=self.settings.cargo_check_cmd,
                forge_cmd=self.settings.forge_test_cmd,
            )
            if not ok:
                req.state = "error"
                req.error = err or "sanity checks failed"
                reset_hard(repo_path, f"{self.settings.push_remote}/{base_branch}")
                return

            req.diff_stat = get_diff_stat(repo_path)

            # No unilateral pushes: ALWAYS require explicit operator approval.
            req.state = "pending_approval"

            # Wait for approval/deny from the operator.
            done, _ = await asyncio.wait(
                [
                    asyncio.create_task(req.approved.wait()),
                    asyncio.create_task(req.denied.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            _ = done

            if req.denied.is_set():
                req.state = "denied"
                reset_hard(repo_path, f"{self.settings.push_remote}/{base_branch}")
                return

            # Approved: commit + push.
            req.state = "approved"

            commit_msg = f"slm: {req_id[:8]}"
            ok, err, commit_sha = await asyncio.to_thread(
                stage_commit_and_push,
                repo_path,
                branch=branch,
                base_branch=base_branch,
                push_remote=self.settings.push_remote,
                github_token=self.settings.github_token,
                commit_message=commit_msg,
            )
            if not ok:
                req.state = "error"
                req.error = err
                reset_hard(repo_path, f"{self.settings.push_remote}/{base_branch}")
                return

            req.commit = commit_sha
            req.state = "pushed"

        except Exception as e:
            req.state = "error"
            req.error = str(e)


def _run_subprocess(cmd: list[str]) -> None:
    import subprocess

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


__all__ = ["SLMService", "ChangeRequest"]
