from .junior_whole_prompts import JuniorWholePrompts
from .whole_coder import WholeCoder


class JuniorWholeCoder(WholeCoder):
    edit_format = "junior-whole"
    gpt_prompts = JuniorWholePrompts()
