import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from aider.providers.base import BaseProvider, ProviderEvent

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(BaseProvider):
    def __init__(self):
        self._session_id: str | None = None

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        from claude_agent_sdk import ClaudeAgentOptions, query
        from claude_agent_sdk import RateLimitEvent

        async for msg in query(
            prompt=prompt,
            options=ClaudeAgentOptions(resume=self._session_id),
        ):
            if hasattr(msg, "session_id") and msg.session_id:
                self._session_id = msg.session_id

            if isinstance(msg, RateLimitEvent):
                info = msg.rate_limit_info
                if info.status == "rejected":
                    reset_at = (
                        datetime.fromtimestamp(info.resets_at, tz=timezone.utc).isoformat()
                        if info.resets_at
                        else None
                    )
                    yield ProviderEvent(type="exhausted", reset_at=reset_at)
                    return
                elif info.status == "allowed_warning":
                    logger.warning(
                        "Claude Code approaching usage limit (utilization=%.0f%%)",
                        (info.utilization or 0) * 100,
                    )

            elif hasattr(msg, "result") and msg.result:
                yield ProviderEvent(type="text", content=msg.result)

            elif hasattr(msg, "error") and msg.error:
                yield ProviderEvent(type="error", content=str(msg.error))

        yield ProviderEvent(type="done", session_id=self._session_id)

    @property
    def current_session_id(self) -> str | None:
        return self._session_id
