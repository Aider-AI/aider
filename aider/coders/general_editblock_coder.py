from .editblock_coder import EditBlockCoder
from .general_editblock_prompts import GeneralEditBlockPrompts


class GeneralEditBlockCoder(EditBlockCoder):
    """A coder that uses search/replace blocks for general document editing."""

    edit_format = "general"
    gpt_prompts = GeneralEditBlockPrompts()
