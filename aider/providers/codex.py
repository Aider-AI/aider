import asyncio
import json
import logging
from collections.abc import AsyncIterator

from aider.providers.base import BaseProvider, ProviderEvent

logger = logging.getLogger(__name__)

_BENIGN_STDERR = "failed to record rollout items"


class CodexProvider(BaseProvider):
    def __init__(self, sandbox: str = "workspace-write"):
        self._thread_id: str | None = None
        self._sandbox = sandbox

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        if self._thread_id is None:
            cmd = ["codex", "exec", "--json", "--sandbox", self._sandbox, prompt]
        else:
            cmd = [
                "codex",
                "exec",
                "resume",
                self._thread_id,
                prompt,
                "--json",
                "--sandbox",
                self._sandbox,
            ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async for raw in proc.stdout:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("codex non-json stdout: %s", line)
                continue

            match event.get("type"):
                case "thread.started":
                    self._thread_id = event["thread_id"]
                case "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        yield ProviderEvent(type="text", content=item.get("text", ""))
                case "turn.failed":
                    err = event.get("error", {})
                    if err.get("code") == "rate_limit_exceeded":
                        yield ProviderEvent(type="exhausted")
                    else:
                        yield ProviderEvent(type="error", content=str(err))
                case "turn.completed":
                    yield ProviderEvent(type="done", session_id=self._thread_id)
                case _:
                    logger.debug("codex unhandled event: %s", event.get("type"))

        stderr = (await proc.stderr.read()).decode().strip()
        for line in stderr.splitlines():
            if _BENIGN_STDERR in line:
                logger.debug("codex stderr (benign): %s", line)
            elif line:
                logger.warning("codex stderr: %s", line)

        await proc.wait()

    @property
    def current_session_id(self) -> str | None:
        return self._thread_id
