from .ask_prompts import AskPrompts
from .base_coder import Coder


class AskCoder(Coder):
    edit_format = "ask"
    gpt_prompts = AskPrompts()
