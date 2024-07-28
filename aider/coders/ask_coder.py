from pathlib import Path

from aider import diffs

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .ask_prompts import AskPrompts


class AskCoder(Coder):
    edit_format = "ask"
    gpt_prompts = AskPrompts()
