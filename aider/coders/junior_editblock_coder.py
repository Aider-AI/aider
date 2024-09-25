from .editblock_coder import EditBlockCoder
from .junior_editblock_prompts import JuniorEditBlockPrompts


class JuniorEditBlockCoder(EditBlockCoder):
    edit_format = "junior-diff"
    gpt_prompts = JuniorEditBlockPrompts()
