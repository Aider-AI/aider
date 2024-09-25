from .base_coder import Coder
from .junior_editblock_prompts import JuniorEditBlockPrompts


class JuniorEditBlockCoder(EditBlockCoder):
    edit_format = "junior-diff"
    gpt_prompts = JuniorEditBlockPrompts()
