from aider.coders.base_coder_auto_approve import AutoApproveCoder
from .architect_prompts import ArchitectPrompts


class AutoApproveAskCoder(AutoApproveCoder):
    """Ask questions about code without making any changes."""

    edit_format = "askv2"
    gpt_prompts = ArchitectPrompts()
