from .ask_prompts import AskPrompts
from .base_coder import Coder
from .base_prompts import CoderPrompts


class AskCoder(Coder):
    """Ask questions about code without making any changes."""

    edit_format = "ask"
    gpt_prompts: CoderPrompts = AskPrompts()
