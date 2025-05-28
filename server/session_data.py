from typing import List

from pydantic import BaseModel


class SessionPrompt(BaseModel):
    timestamp: float
    prompt: str


class SessionData(BaseModel):
    prompts: List[SessionPrompt] = []
