from .ask_coder import AskCoder
from .senior_prompts import SeniorPrompts


class SeniorCoder(AskCoder):
    edit_format = "senior"
    gpt_prompts = SeniorPrompts()
