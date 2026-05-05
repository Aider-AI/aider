import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from aider.providers.base import BaseProvider, ProviderEvent

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(BaseProvider):
    def __init__(self):
        self._session_id: str | None = None

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        from claude_agent_sdk import ClaudeAgentOptions, RateLimitEvent, query
        from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

        async for msg in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                resume=self._session_id,
                permission_mode="acceptEdits",
            ),
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

            elif isinstance(msg, AssistantMessage):
                for block in msg.content or []:
                    if isinstance(block, TextBlock):
                        yield ProviderEvent(type="text", content=block.text)
                    elif hasattr(block, "name") and hasattr(block, "input"):
                        # ToolUseBlock — show the tool call so the user sees progress
                        tool_input = str(block.input) if block.input else ""
                        yield ProviderEvent(
                            type="text",
                            content=f"\n[tool: {block.name} {tool_input[:80]}]\n",
                        )
                if msg.error:
                    yield ProviderEvent(type="error", content=str(msg.error))

            elif isinstance(msg, ResultMessage):
                if msg.session_id:
                    self._session_id = msg.session_id

        yield ProviderEvent(type="done", session_id=self._session_id)

    @property
    def current_session_id(self) -> str | None:
        return self._session_id
