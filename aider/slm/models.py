from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1)


class PromptResponse(BaseModel):
    id: str
    state: str


class ApproveResponse(BaseModel):
    id: str
    state: str


class StatusResponse(BaseModel):
    running_id: str | None
    queued: int
    pending: int
    total: int


class PendingItem(BaseModel):
    id: str
    prompt: str
    state: Literal[
        "queued",
        "running",
        "pending_approval",
        "approved",
        "pushed",
        "denied",
        "error",
        "no_changes",
    ]
    branch: str | None = None
    base_branch: str | None = None
    base_commit: str | None = None
    commit: str | None = None
    diff_stat: str | None = None
    error: str | None = None


class PendingResponse(BaseModel):
    items: list[PendingItem]
