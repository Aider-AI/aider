from pathlib import Path

from aider import diffs

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .chat_prompts import ChatPrompts


class ChatCoder(Coder):
    edit_format = "chat"
    gpt_prompts = ChatPrompts()

    def get_edits(self, mode="update"):
        return

    def apply_edits(self, edits):
        return
