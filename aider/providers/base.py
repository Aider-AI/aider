from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

ProviderTier = Literal["agentic_cli", "completion_api", "hybrid"]


@dataclass
class ProviderEvent:
    type: str  # "text" | "exhausted" | "error" | "done"
    content: str = ""
    reset_at: str | None = None  # ISO timestamp if exhausted
    session_id: str | None = None


class BaseProvider(ABC):
    @abstractmethod
    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]: ...

    @property
    @abstractmethod
    def current_session_id(self) -> str | None: ...

    @property
    def tier(self) -> ProviderTier:
        return "agentic_cli"
