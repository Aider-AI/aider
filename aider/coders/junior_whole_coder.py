from .whole_coder import WholeCoder
from .junior_whole_prompts import JuniorWholePrompts


class JuniorWholeCoder(WholeCoder):
    edit_format = "junior-whole"
    gpt_prompts = JuniorWholePrompts()
