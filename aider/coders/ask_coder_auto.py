from aider.coders.base_coder_auto_approve import AutoApproveCoder
from .architect_prompts import ArchitectPrompts

class AutoApproveAskCoder(AutoApproveCoder):
    """
    A coder that asks questions about the code without automatically
    applying any changes.

    Extends AutoApproveCoder, which provides functionality for automatically
    approving and running the model's proposed changes. This class overrides
    the edit_format and gpt_prompts attributes to customize the coder's behavior.

    questions about the code without automatically applying any changes.
    It uses the 'askv2' edit format and ArchitectPrompts for generating prompts.
    """

    edit_format = "askv2"
    gpt_prompts = ArchitectPrompts()
