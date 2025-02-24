from .ask_coder import AskCoder
from .compiler_prompts import CompilerPrompts


class CompilerCoder(AskCoder):
    """Compiles implementation instructions from architects' proposals."""

    edit_format = "ask"
    gpt_prompts = CompilerPrompts()
