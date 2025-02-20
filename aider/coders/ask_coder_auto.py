from aider.coders.base_coder_auto_approve import AutoApproveCoder
from .architect_prompts import ArchitectPrompts

class AutoApproveAskCoder(AutoApproveCoder):
    """
    This class extends AutoApproveCoder to implement a coder that asks
    questions about the code without automatically applying any changes.
    It uses the 'askv2' edit format and ArchitectPrompts for generating prompts.
    """

    edit_format = "askv2"
    gpt_prompts = ArchitectPrompts()
