from aider.coders.base_coder_auto_approve import AutoApproveCoder
from .ask_prompts import AskPrompts
from .base_coder import Coder


class AutoApproveAskCoder(AutoApproveCoder):
    """Ask questions about code without making any changes."""

    edit_format = "askv2"
    gpt_prompts = AskPrompts()
