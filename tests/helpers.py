"""Shared test utilities for relay tests."""
from collections.abc import AsyncIterator

from aider.providers.base import BaseProvider, ProviderEvent


class MockProvider(BaseProvider):
    """Provider that emits a fixed sequence of events per turn."""

    def __init__(self, turns: list[list[ProviderEvent]], session_id: str = "mock-session"):
        self._turns = list(turns)
        self._session_id = session_id
        self.prompts_received: list[str] = []

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        self.prompts_received.append(prompt)
        events = self._turns.pop(0) if self._turns else [ProviderEvent(type="done")]
        for event in events:
            yield event

    @property
    def current_session_id(self) -> str | None:
        return self._session_id


def success_turn(text: str = "ok") -> list[ProviderEvent]:
    return [ProviderEvent(type="text", content=text), ProviderEvent(type="done")]


def exhausted_turn(reset_at: str | None = None) -> list[ProviderEvent]:
    return [ProviderEvent(type="exhausted", reset_at=reset_at)]


def error_turn(msg: str = "something went wrong") -> list[ProviderEvent]:
    return [ProviderEvent(type="error", content=msg), ProviderEvent(type="done")]
