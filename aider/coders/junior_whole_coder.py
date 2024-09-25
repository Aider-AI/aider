from .junior_whole_prompts import JuniorWholeFilePrompts
from .wholefile_coder import WholeFileCoder


class JuniorWholeFileCoder(WholeFileCoder):
    edit_format = "junior-whole"
    gpt_prompts = JuniorWholeFilePrompts()
